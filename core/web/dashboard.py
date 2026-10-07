"""
Web dashboard. Serves a status page and a JSON endpoint with the state of the bot and of
every Crafty server, and lets the feature flags be switched (only with ``WEB_PASSWORD``).
Only loaded when ``WEB_ENABLED=true``.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import errno
import hmac
import logging
import math
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Union

from aiohttp import web
from discord.ext import commands

from core import __version__
from core.crafty import CraftyAPIError, JsonDict, busy_state, player_count, player_names
from core.flags import FlagError, FlagSaveError
from core.formatting import format_memory
from core.log import LEVELS, LOG_BUFFER, get_log_level, set_log_level

if TYPE_CHECKING:
    from core.bot import CraftyBot

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / 'static'
SNAPSHOT_CACHE_TTL = 15  # seconds, so page refreshes don't hammer Crafty
STATIC_FILES = {
    '/': ('index.html', 'text/html'),
    '/app.js': ('app.js', 'text/javascript'),
    '/app.css': ('app.css', 'text/css'),
}
# Sent by app.js on every write. Browsers only allow custom headers on cross-origin requests after a
# CORS preflight, which this server never answers, so other sites can't change flags (CSRF).
CSRF_HEADER = 'X-Crafty-Bot'
MAX_LOG_ENTRIES = 500  # per request
SECURITY_HEADERS = {
    'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                               "img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
}

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


class DashboardStartError(Exception):
    """Raised when the web server of the dashboard can't be started."""


def describe_bind_error(exc: OSError, host: str, port: int) -> str:
    """Turn the error of binding the web server into a message that says what to change."""
    if exc.errno == errno.EADDRINUSE:
        return f'port {port} is already in use, set WEB_PORT to a free port or stop the other program'
    if exc.errno == errno.EACCES:
        return f'no permission to use port {port}, use a port above 1023'
    # asyncio drops the errno of EADDRNOTAVAIL and only says it could not bind on any address.
    if (exc.errno == errno.EADDRNOTAVAIL or isinstance(exc, socket.gaierror)
            or str(exc).startswith('could not bind on any address')):
        return f'WEB_HOST {host!r} is not an address of this machine, use 127.0.0.1 or 0.0.0.0'
    return str(exc)


def summarize_server(server: JsonDict, stats: Optional[JsonDict], error: Optional[str] = None) -> Dict[str, Any]:
    """Reduce a server and its stats to what the dashboard shows."""
    stats = stats or {}
    running = bool(stats.get('running'))
    version = stats.get('version')
    return {
        'id': server.get('server_id'),
        'name': server.get('server_name') or server.get('server_id'),
        'type': server.get('type'),
        'address': f"{server['server_ip']}:{server.get('server_port', '?')}" if server.get('server_ip') else None,
        'running': running,
        'state': busy_state(stats) or ('crashed' if stats.get('crashed') else None),
        'players': player_count(stats) if running else None,
        'max_players': stats.get('max') or None,
        'player_names': player_names(stats) if running else [],
        'version': version if running and version and version != 'False' else None,
        'cpu': stats.get('cpu') if running else None,
        'memory': format_memory(stats.get('mem')) if running else None,
        'memory_percent': stats.get('mem_percent') if running else None,
        'error': error,
    }


class WebDashboard(commands.Cog):
    """Runs the web server of the dashboard while the cog is loaded."""

    def __init__(self, bot: CraftyBot):
        self.bot = bot
        self._started = time.monotonic()
        self._runner: Optional[web.AppRunner] = None
        self._snapshot: Optional[Dict[str, Any]] = None
        self._snapshot_time = 0.0
        self._snapshot_lock = asyncio.Lock()
        self.app = self._create_app()

    def _create_app(self) -> web.Application:
        app = web.Application(middlewares=[self._security_middleware])
        app.router.add_get('/healthz', self._health)
        app.router.add_get('/api/status', self._status)
        app.router.add_get('/api/flags', self._get_flags)
        app.router.add_put('/api/flags/{name}', self._set_flag)
        app.router.add_get('/api/logs', self._get_logs)
        app.router.add_put('/api/log-level', self._set_log_level)
        for path, (file_name, content_type) in STATIC_FILES.items():
            app.router.add_get(path, self._static_handler(file_name, content_type))
        return app

    async def cog_load(self) -> None:
        """
        Start the web server.

        Raises:
            DashboardStartError: If the server can't listen on WEB_HOST:WEB_PORT. Nothing is
                left running in that case.
        """
        settings = self.bot.settings
        runner = web.AppRunner(self.app, access_log=None)
        await runner.setup()
        try:
            await web.TCPSite(runner, settings.web_host, settings.web_port).start()
        except OSError as exc:
            await runner.cleanup()
            raise DashboardStartError(
                f'Cannot start the web dashboard on {settings.web_host}:{settings.web_port}: '
                f'{describe_bind_error(exc, settings.web_host, settings.web_port)}') from exc
        self._runner = runner
        logger.info('Web dashboard running on http://%s:%d%s', settings.web_host, settings.web_port,
                    '' if settings.web_password else ' (no WEB_PASSWORD set, anyone who can reach it can see it)')

    async def cog_unload(self) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            logger.info('Web dashboard stopped')

    @web.middleware
    async def _security_middleware(self, request: web.Request, handler: Handler) -> web.StreamResponse:
        if request.path != '/healthz' and not self._authorized(request):
            logger.debug('Unauthorized dashboard request from %s', request.remote)
            response: web.StreamResponse = web.Response(
                status=401, text='Unauthorized', headers={'WWW-Authenticate': 'Basic realm="Crafty Bot"'})
        else:
            response = await handler(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    def _authorized(self, request: web.Request) -> bool:
        """Check the HTTP basic auth password (the user name is ignored) if one is configured."""
        expected = self.bot.settings.web_password
        if not expected:
            return True
        scheme, _, encoded = request.headers.get('Authorization', '').partition(' ')
        if scheme.lower() != 'basic':
            return False
        try:
            credentials = base64.b64decode(encoded, validate=True).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            return False
        password = credentials.partition(':')[2]
        return hmac.compare_digest(password.encode('utf-8'), expected.encode('utf-8'))

    @staticmethod
    def _static_handler(file_name: str, content_type: str) -> Handler:
        async def handler(_request: web.Request) -> web.StreamResponse:
            try:
                body = (STATIC_DIR / file_name).read_bytes()
            except OSError as exc:
                logger.error('Dashboard file %s cannot be read: %s', file_name, exc)
                return web.Response(status=500, text='Dashboard files are missing, check the bot logs.')
            return web.Response(body=body, content_type=content_type, charset='utf-8')
        return handler

    @staticmethod
    async def _health(_request: web.Request) -> web.StreamResponse:
        return web.Response(text='ok')

    async def _status(self, _request: web.Request) -> web.StreamResponse:
        try:
            return web.json_response(await self.snapshot())
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception('Unexpected error while collecting the dashboard status')
            return web.json_response({'error': 'Internal error, check the bot logs.'}, status=500)

    @property
    def editable(self) -> bool:
        """Settings can only be changed when the dashboard is protected by a password."""
        return bool(self.bot.settings.web_password)

    async def _write_request_body(self, request: web.Request, what: str) -> Union[Dict[str, Any], web.Response]:
        """
        Check a request that changes something and return its JSON object body, or the error
        response to send instead.
        """
        if not self.editable:
            return web.json_response({'error': f'Set WEB_PASSWORD to change {what}.'}, status=403)
        if request.headers.get(CSRF_HEADER) != '1' or request.content_type != 'application/json':
            logger.warning('Rejected change of %s without CSRF header from %s', what, request.remote)
            return web.json_response({'error': 'Invalid request.'}, status=400)
        try:
            body = await request.json()
        except ValueError:
            return web.json_response({'error': 'Invalid JSON.'}, status=400)
        if not isinstance(body, dict):
            return web.json_response({'error': 'Expected a JSON object.'}, status=400)
        return body

    def _flags_response(self) -> web.Response:
        return web.json_response({'flags': self.bot.flags.as_list(), 'editable': self.editable})

    async def _get_flags(self, _request: web.Request) -> web.StreamResponse:
        return self._flags_response()

    async def _set_flag(self, request: web.Request) -> web.StreamResponse:
        body = await self._write_request_body(request, 'feature flags')
        if isinstance(body, web.Response):
            return body

        name = request.match_info['name']
        enabled = body.get('enabled')
        try:
            self.bot.flags.set(name, enabled)
        except FlagSaveError as exc:
            logger.error('%s', exc)
            return web.json_response({'error': 'The flag could not be saved, check the bot logs.'}, status=500)
        except FlagError as exc:
            logger.warning('Feature flag change from %s failed: %s', request.remote, exc)
            return web.json_response({'error': str(exc)}, status=400)
        logger.info('Feature flag %s %s from the dashboard (%s)', name, 'enabled' if enabled else 'disabled',
                    request.remote)
        self._snapshot = None  # the bot status shows the auto stop flag
        return self._flags_response()

    async def _get_logs(self, request: web.Request) -> web.StreamResponse:
        try:
            after = max(int(request.query.get('after', 0)), 0)
        except ValueError:
            return web.json_response({'error': 'after must be a number.'}, status=400)
        return web.json_response({
            'entries': LOG_BUFFER.entries(after, MAX_LOG_ENTRIES),
            'level': get_log_level(),
            'levels': list(LEVELS),
            'editable': self.editable,
        })

    async def _set_log_level(self, request: web.Request) -> web.StreamResponse:
        body = await self._write_request_body(request, 'the log level')
        if isinstance(body, web.Response):
            return body

        level = str(body.get('level', '')).upper()
        if level not in LEVELS:
            return web.json_response({'error': f"Log level must be one of {', '.join(LEVELS)}."}, status=400)
        previous = get_log_level()
        set_log_level(level)
        # WARNING, so the change is visible whatever the new level is.
        logger.warning('Log level changed from %s to %s in the dashboard (%s), until the next restart',
                       previous, level, request.remote)
        return web.json_response({'level': get_log_level()})

    async def snapshot(self) -> Dict[str, Any]:
        """Return the current status, cached for a few seconds."""
        async with self._snapshot_lock:
            now = time.monotonic()
            if self._snapshot is None or now - self._snapshot_time >= SNAPSHOT_CACHE_TTL:
                self._snapshot = await self._collect()
                self._snapshot_time = now
            return self._snapshot

    async def _collect(self) -> Dict[str, Any]:
        servers: List[Dict[str, Any]] = []
        error = None
        try:
            server_list = await self.bot.crafty.list_servers()
        except CraftyAPIError as exc:
            logger.warning('Dashboard could not load the server list: %s', exc)
            error = 'Crafty Controller is not reachable. Check the bot logs for details.'
        else:
            server_list = [server for server in server_list if server.get('server_id')]
            results = await asyncio.gather(*(self.bot.crafty.get_stats(server['server_id'])
                                             for server in server_list), return_exceptions=True)
            for server, result in zip(server_list, results):
                if isinstance(result, CraftyAPIError):
                    logger.warning('Dashboard could not load the stats of %s: %s', server.get('server_id'), result)
                    servers.append(summarize_server(server, None, 'Stats not available'))
                elif isinstance(result, BaseException):
                    logger.error('Unexpected error while loading the stats of %s', server.get('server_id'),
                                 exc_info=result)
                    servers.append(summarize_server(server, None, 'Stats not available'))
                else:
                    servers.append(summarize_server(server, result))

        return {
            'bot': self._bot_status(),
            'servers': servers,
            'error': error,
            'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        }

    def _bot_status(self) -> Dict[str, Any]:
        latency = self.bot.latency
        settings = self.bot.settings
        return {
            'connected': self.bot.is_ready() and not self.bot.is_closed(),
            'user': str(self.bot.user) if self.bot.user else None,
            'version': __version__,
            'latency_ms': round(latency * 1000) if math.isfinite(latency) else None,
            'guilds': len(self.bot.guilds),
            'uptime_seconds': round(time.monotonic() - self._started),
            'auto_stop': settings.auto_stop_interval if self.bot.flags.is_enabled('auto_stop') else None,
        }
