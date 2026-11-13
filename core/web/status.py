"""Collects the status of the bot and of every Crafty server for the dashboard."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core import __version__
from core.crafty import CraftyAPIError, JsonDict, busy_state, player_count, player_names, server_version
from core.formatting import format_memory

if TYPE_CHECKING:
    from core.bot import CraftyBot

logger = logging.getLogger(__name__)

SNAPSHOT_CACHE_TTL = 15  # seconds, so page refreshes don't hammer Crafty


def summarize_server(server: JsonDict, stats: Optional[JsonDict], error: Optional[str] = None) -> Dict[str, Any]:
    """Reduce a server and its stats to what the dashboard shows."""
    stats = stats or {}
    running = bool(stats.get('running'))
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
        'version': server_version(stats),
        'cpu': stats.get('cpu') if running else None,
        'memory': format_memory(stats.get('mem')) if running else None,
        'memory_percent': stats.get('mem_percent') if running else None,
        'error': error,
    }


class StatusCollector:
    """Builds the status snapshot and caches it for a few seconds."""

    def __init__(self, bot: CraftyBot):
        """Create the collector for the given bot."""
        self.bot = bot
        self._started = time.monotonic()
        self._snapshot: Optional[Dict[str, Any]] = None
        self._snapshot_time = 0.0
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        """Rebuild the snapshot on the next request, e.g. after a feature flag changed."""
        self._snapshot = None

    async def snapshot(self) -> Dict[str, Any]:
        """Return the current status, cached for a few seconds."""
        async with self._lock:
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
