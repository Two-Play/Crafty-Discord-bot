"""
Read-only web dashboard. Serves a status page and a JSON endpoint with the state of the
bot and of every Crafty server. Only loaded when ``WEB_ENABLED=true``.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hmac
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from aiohttp import web
from discord.ext import commands

from core import __version__
from core.crafty import CraftyAPIError, JsonDict, busy_state, player_count, player_names
from core.formatting import format_memory

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
SECURITY_HEADERS = {
    'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                               "img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
}

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


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
        for path, (file_name, content_type) in STATIC_FILES.items():
            app.router.add_get(path, self._static_handler(file_name, content_type))
        return app

    async def cog_load(self) -> None:
        self._runner = web.AppRunner(self.app, access_log=None)
        await self._runner.setup()
        settings = self.bot.settings
        await web.TCPSite(self._runner, settings.web_host, settings.web_port).start()
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
            body = (STATIC_DIR / file_name).read_bytes()
            return web.Response(body=body, content_type=content_type, charset='utf-8')
        return handler

    @staticmethod
    async def _health(_request: web.Request) -> web.StreamResponse:
        return web.Response(text='ok')

    async def _status(self, _request: web.Request) -> web.StreamResponse:
        return web.json_response(await self.snapshot())

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
            'auto_stop': settings.auto_stop_interval if settings.auto_stop_enabled else None,
        }
