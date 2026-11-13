"""
Web dashboard. Serves a status page and a JSON endpoint with the state of the bot and of
every Crafty server, and lets the feature flags be switched (only with ``WEB_PASSWORD``).
Only loaded when ``WEB_ENABLED=true``.
"""

from __future__ import annotations

import errno
import logging
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from aiohttp import web
from discord.ext import commands

from core.config import LOG_LEVELS
from core.flags import FlagError, FlagSaveError
from core.log import LOG_BUFFER, get_log_level, set_log_level
from core.web.security import CSRF_HEADER, Handler, security_middleware
from core.web.status import StatusCollector

if TYPE_CHECKING:
    from core.bot import CraftyBot

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / 'static'
STATIC_FILES = {
    '/': ('index.html', 'text/html'),
    '/app.js': ('app.js', 'text/javascript'),
    '/app.css': ('app.css', 'text/css'),
}
MAX_LOG_ENTRIES = 500  # per request


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


class WebDashboard(commands.Cog):
    """Runs the web server of the dashboard while the cog is loaded."""

    def __init__(self, bot: CraftyBot):
        self.bot = bot
        self.status = StatusCollector(bot)
        self._runner: Optional[web.AppRunner] = None
        self._static_cache: Dict[str, bytes] = {}
        self.app = self._create_app()

    def _create_app(self) -> web.Application:
        app = web.Application(middlewares=[security_middleware(self.bot.settings)])
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

    def _static_handler(self, file_name: str, content_type: str) -> Handler:
        async def handler(_request: web.Request) -> web.StreamResponse:
            body = self._static_cache.get(file_name)
            if body is None:
                try:
                    body = (STATIC_DIR / file_name).read_bytes()
                except OSError as exc:
                    logger.error('Dashboard file %s cannot be read: %s', file_name, exc)
                    return web.Response(status=500, text='Dashboard files are missing, check the bot logs.')
                self._static_cache[file_name] = body
            return web.Response(body=body, content_type=content_type, charset='utf-8')
        return handler

    @staticmethod
    async def _health(_request: web.Request) -> web.StreamResponse:
        return web.Response(text='ok')

    async def _status(self, _request: web.Request) -> web.StreamResponse:
        try:
            return web.json_response(await self.status.snapshot())
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
        self.status.invalidate()  # the bot status shows the auto stop flag
        return self._flags_response()

    async def _get_logs(self, request: web.Request) -> web.StreamResponse:
        try:
            after = max(int(request.query.get('after', 0)), 0)
        except ValueError:
            return web.json_response({'error': 'after must be a number.'}, status=400)
        return web.json_response({
            'entries': LOG_BUFFER.entries(after, MAX_LOG_ENTRIES),
            # Lower than the client's last ID after a restart of the bot, so it starts over.
            'last_id': LOG_BUFFER.last_id,
            'level': get_log_level(),
            'levels': list(LOG_LEVELS),
            'editable': self.editable,
        })

    async def _set_log_level(self, request: web.Request) -> web.StreamResponse:
        body = await self._write_request_body(request, 'the log level')
        if isinstance(body, web.Response):
            return body

        level = str(body.get('level', '')).upper()
        if level not in LOG_LEVELS:
            return web.json_response({'error': f"Log level must be one of {', '.join(LOG_LEVELS)}."}, status=400)
        previous = get_log_level()
        set_log_level(level)
        # WARNING, so the change is visible whatever the new level is.
        logger.warning('Log level changed from %s to %s in the dashboard (%s), until the next restart',
                       previous, level, request.remote)
        return web.json_response({'level': get_log_level()})
