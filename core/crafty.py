"""
Client for the Crafty Controller 4 REST API.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
import urllib3

logger = logging.getLogger(__name__)

SERVERS_ENDPOINT = '/api/v2/servers'
LOGIN_ENDPOINT = '/api/v2/auth/login'
DEFAULT_TIMEOUT = 6  # seconds
MAX_LOGGED_BODY_LENGTH = 300

JsonDict = Dict[str, Any]


class CraftyAPIError(Exception):
    """Raised when a request to the Crafty API fails."""


class ServerAction(str, Enum):
    """Power actions that can be executed on a server."""

    START = 'start_server'
    STOP = 'stop_server'
    RESTART = 'restart_server'
    BACKUP = 'backup_server'


def parse_server_id(value: str) -> Optional[str]:
    """
    Return the canonical form of a server ID (a UUID), or ``None`` if it is invalid.
    """
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _is_true(value: Any) -> bool:
    """Crafty returns some flags as booleans and others as the strings 'True'/'False'."""
    return value is True or str(value).lower() == 'true'


def player_count(stats: JsonDict) -> Optional[int]:
    """
    Return the number of players online, or ``None`` if it is unknown.

    Crafty gets the player count by pinging the server. If the ping fails (the server is
    still starting, doesn't answer pings, or the port is configured wrong), ``online`` is
    reported as 0, so 0 only counts if ``int_ping_results`` says the ping worked.
    """
    online = stats.get('online')
    if isinstance(online, int) and not isinstance(online, bool) and online > 0:
        return online
    if _is_true(stats.get('int_ping_results')):
        return 0
    return None


def player_names(stats: JsonDict) -> List[str]:
    """Return the names of the online players (Crafty sends them as a stringified list)."""
    players = stats.get('players')
    if isinstance(players, str):
        try:
            players = ast.literal_eval(players)
        except (ValueError, SyntaxError):
            return []
    if not isinstance(players, (list, tuple)):
        return []
    return [str(player) for player in players]


def busy_state(stats: JsonDict) -> Optional[str]:
    """Return what the server is busy with (starting, updating, importing), or ``None``."""
    for field, state in (('waiting_start', 'starting'), ('updating', 'updating'), ('importing', 'importing')):
        if _is_true(stats.get(field)):
            return state
    return None


def server_version(stats: JsonDict) -> Optional[str]:
    """Return the game version of a running server, or ``None`` (Crafty sends ``"False"`` when unknown)."""
    version = stats.get('version')
    if not stats.get('running') or not version or version == 'False':
        return None
    return str(version)


def _shorten(text: str, length: int) -> str:
    return text if len(text) <= length else text[:length] + '...'


class CraftyClient:
    """
    Thin wrapper around the Crafty API.

    The public methods are coroutines. The blocking HTTP requests run in a worker
    thread so they don't block the Discord event loop.
    """

    def __init__(self, base_url: str, token: str = '', *, verify_ssl: bool = False,
                 timeout: float = DEFAULT_TIMEOUT, session: Optional[requests.Session] = None):
        self._base_url = base_url.rstrip('/')
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._session = session or requests.Session()
        if token:
            self.set_token(token)
        if not verify_ssl:
            # Crafty usually runs with a self-signed certificate.
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def set_token(self, token: str) -> None:
        """Use the given API token for all following requests."""
        self._session.headers['Authorization'] = f'Bearer {token}'

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def _request(self, method: str, path: str, payload: Optional[JsonDict] = None, *,
                 envelope: bool = True) -> Any:
        """
        Send a request and return the decoded body.

        With ``envelope`` the body must be ``{"status": "ok", ...}``. Without it (the backup
        endpoints answer with the bare data) only an explicit ``"status": "error"`` fails.
        """
        start = time.monotonic()
        try:
            response = self._session.request(method, self._base_url + path, json=payload,
                                             timeout=self._timeout, verify=self._verify_ssl)
        except requests.RequestException as exc:
            raise CraftyAPIError(f'{method} {path} failed: {exc}') from exc
        logger.debug('%s %s -> HTTP %d (%.0f ms)', method, path, response.status_code,
                     (time.monotonic() - start) * 1000)

        if not response.ok:
            raise CraftyAPIError(f'{method} {path} returned HTTP {response.status_code}')
        try:
            body = response.json()
        except ValueError as exc:
            raise CraftyAPIError(f'{method} {path} returned invalid JSON') from exc
        status = body.get('status') if isinstance(body, dict) else None
        if (envelope and status != 'ok') or status == 'error':
            raise CraftyAPIError(f'{method} {path} returned an error: '
                                 f'{_shorten(repr(body), MAX_LOGGED_BODY_LENGTH)}')
        return body

    async def _call(self, method: str, path: str, payload: Optional[JsonDict] = None, *,
                    envelope: bool = True) -> Any:
        return await asyncio.to_thread(self._request, method, path, payload, envelope=envelope)

    async def _get_data(self, path: str) -> Any:
        """GET an endpoint and return its ``data`` field."""
        body = await self._call('GET', path)
        if 'data' not in body:
            raise CraftyAPIError(f'GET {path} returned no data: {_shorten(repr(body), MAX_LOGGED_BODY_LENGTH)}')
        return body['data']

    async def login(self, username: str, password: str) -> None:
        """Log in with username and password and use the returned token from now on."""
        body = await self._call('POST', LOGIN_ENDPOINT, {'username': username, 'password': password})
        try:
            token = body['data']['token']
        except (KeyError, TypeError) as exc:
            raise CraftyAPIError('Login response did not contain a token') from exc
        self.set_token(token)
        logger.debug('Using the token from the login of %s', username)

    async def list_servers(self) -> List[JsonDict]:
        """Return all servers visible to the API user."""
        servers = await self._get_data(SERVERS_ENDPOINT)
        if not isinstance(servers, list):
            raise CraftyAPIError(f'Unexpected server list: {_shorten(repr(servers), MAX_LOGGED_BODY_LENGTH)}')
        return servers

    async def get_stats(self, server_id: str) -> JsonDict:
        """Return the current statistics (running state, players, CPU, RAM...) of a server."""
        stats = await self._get_data(f'{SERVERS_ENDPOINT}/{server_id}/stats')
        if not isinstance(stats, dict):
            raise CraftyAPIError(f'Unexpected stats: {_shorten(repr(stats), MAX_LOGGED_BODY_LENGTH)}')
        return stats

    async def run_action(self, server_id: str, action: ServerAction, action_id: Optional[str] = None) -> None:
        """Execute an action (start, stop, restart, backup) on a server."""
        path = f'{SERVERS_ENDPOINT}/{server_id}/action/{action.value}'
        if action_id:
            path += f'/{action_id}'
        await self._call('POST', path)

    async def list_backups(self, server_id: str) -> List[JsonDict]:
        """
        Return the backup configurations of a server.

        Needs the BACKUP permission. Crafty returns them as a dict keyed by backup ID and,
        unlike the other endpoints, without the ``{"status", "data"}`` envelope.
        """
        body = await self._call('GET', f'{SERVERS_ENDPOINT}/{server_id}/backups', envelope=False)
        if isinstance(body, dict) and body.get('status') == 'ok':
            body = body.get('data')
        if isinstance(body, dict):
            body = list(body.values())
        if not isinstance(body, list):
            raise CraftyAPIError(f'Unexpected backup list: {_shorten(repr(body), MAX_LOGGED_BODY_LENGTH)}')
        return [backup for backup in body if isinstance(backup, dict) and backup.get('backup_id')]

    async def run_backup(self, server_id: str, backup_id: str) -> None:
        """Start the backup with the given configuration. Crafty runs it in the background."""
        await self.run_action(server_id, ServerAction.BACKUP, backup_id)
