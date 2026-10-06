"""
Client for the Crafty Controller 4 REST API.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
import urllib3

logger = logging.getLogger(__name__)

SERVERS_ENDPOINT = '/api/v2/servers'
LOGIN_ENDPOINT = '/api/v2/auth/login'
DEFAULT_TIMEOUT = 6  # seconds

JsonDict = Dict[str, Any]


class CraftyAPIError(Exception):
    """Raised when a request to the Crafty API fails."""


class ServerAction(str, Enum):
    """Power actions that can be executed on a server."""

    START = 'start_server'
    STOP = 'stop_server'
    RESTART = 'restart_server'


def parse_server_id(value: str) -> Optional[str]:
    """
    Return the canonical form of a server ID (a UUID), or ``None`` if it is invalid.
    """
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


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

    def _request(self, method: str, path: str, payload: Optional[JsonDict] = None) -> JsonDict:
        try:
            response = self._session.request(method, self._base_url + path, json=payload,
                                             timeout=self._timeout, verify=self._verify_ssl)
        except requests.RequestException as exc:
            raise CraftyAPIError(f'{method} {path} failed: {exc}') from exc

        if not response.ok:
            raise CraftyAPIError(f'{method} {path} returned HTTP {response.status_code}')
        try:
            body = response.json()
        except ValueError as exc:
            raise CraftyAPIError(f'{method} {path} returned invalid JSON') from exc
        if not isinstance(body, dict) or body.get('status') != 'ok':
            raise CraftyAPIError(f'{method} {path} returned an error: {body!r}')
        return body

    async def _call(self, method: str, path: str, payload: Optional[JsonDict] = None) -> JsonDict:
        logger.debug('%s %s', method, path)
        return await asyncio.to_thread(self._request, method, path, payload)

    async def login(self, username: str, password: str) -> None:
        """Log in with username and password and use the returned token from now on."""
        body = await self._call('POST', LOGIN_ENDPOINT, {'username': username, 'password': password})
        try:
            token = body['data']['token']
        except (KeyError, TypeError) as exc:
            raise CraftyAPIError('Login response did not contain a token') from exc
        self.set_token(token)

    async def list_servers(self) -> List[JsonDict]:
        """Return all servers visible to the API user."""
        return (await self._call('GET', SERVERS_ENDPOINT))['data']

    async def get_stats(self, server_id: str) -> JsonDict:
        """Return the current statistics (running state, players, CPU, RAM...) of a server."""
        return (await self._call('GET', f'{SERVERS_ENDPOINT}/{server_id}/stats'))['data']

    async def run_action(self, server_id: str, action: ServerAction) -> None:
        """Execute a power action (start, stop, restart) on a server."""
        await self._call('POST', f'{SERVERS_ENDPOINT}/{server_id}/action/{action.value}')
