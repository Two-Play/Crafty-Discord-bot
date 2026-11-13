"""
Background task that stops servers without players.
"""

import logging
from typing import Optional, Set

from discord.ext import commands, tasks

from core.crafty import CraftyAPIError, CraftyClient, ServerAction, busy_state, player_count
from core.flags import FeatureFlags

logger = logging.getLogger(__name__)


class AutoStop(commands.Cog):
    """
    Periodically stops every running server that has no players online.

    A server is only stopped when it was empty at two checks in a row, so it had at least one
    full interval for players to join. Otherwise a server started just before a check (or
    running when the bot starts) would be stopped right away.

    The loop always runs, but only does something while the ``auto_stop`` feature flag is on.
    """

    def __init__(self, client: CraftyClient, interval: int, flags: Optional[FeatureFlags] = None):
        self._client = client
        self._flags = flags
        self._idle: Set[str] = set()  # servers that were empty at the previous check
        self.stop_idle_servers.change_interval(seconds=interval)

    @property
    def enabled(self) -> bool:
        """Whether the ``auto_stop`` feature flag is on."""
        return self._flags is None or self._flags.is_enabled('auto_stop')

    async def cog_load(self) -> None:
        self.stop_idle_servers.start()
        logger.info('Auto stop %s, checking every %d seconds', 'enabled' if self.enabled else 'disabled',
                    self.stop_idle_servers.seconds)

    async def cog_unload(self) -> None:
        self.stop_idle_servers.cancel()

    @tasks.loop(minutes=30)
    async def stop_idle_servers(self) -> None:
        """Stop running servers without players. Errors are logged and retried next run."""
        if not self.enabled:
            logger.debug('Auto stop is disabled by its feature flag, skipping this run')
            self._idle.clear()
            return
        try:
            servers = await self._client.list_servers()
        except CraftyAPIError as exc:
            logger.warning('Auto stop could not load the server list: %s', exc)
            return
        except Exception:  # pylint: disable=broad-exception-caught
            # An unexpected error must not end the loop, which would disable auto stop for good.
            logger.exception('Unexpected error while loading the server list for auto stop')
            return

        stopped = 0
        for server in servers:
            server_id = server.get('server_id')
            if not server_id:
                continue
            name = server.get('server_name') or server_id
            try:
                stopped += await self._stop_if_idle(server_id, name)
            except CraftyAPIError as exc:
                logger.warning('Auto stop failed for server %s (%s): %s', name, server_id, exc)
            except Exception:  # pylint: disable=broad-exception-caught
                # An unexpected error must not end the loop, which would disable auto stop for good.
                logger.exception('Unexpected error in auto stop for server %s (%s)', name, server_id)
        logger.debug('Auto stop checked %d server(s), stopped %d', len(servers), stopped)

    async def _stop_if_idle(self, server_id: str, name: str) -> bool:
        """Stop the server if it was empty at this and the previous check. Returns whether it was stopped."""
        was_idle = server_id in self._idle
        self._idle.discard(server_id)
        stats = await self._client.get_stats(server_id)
        if not stats.get('running'):
            return False

        state = busy_state(stats)
        if state:
            logger.debug('Auto stop: skipping server %s (%s), it is %s', name, server_id, state)
            return False
        players = player_count(stats)
        if players is None:
            logger.info('Auto stop: skipping server %s (%s), player count unknown (Crafty cannot ping it)',
                        name, server_id)
            return False
        if players:
            return False
        if not was_idle:
            self._idle.add(server_id)
            logger.info('Auto stop: server %s (%s) is empty, stopping it at the next check if it still is',
                        name, server_id)
            return False

        await self._client.run_action(server_id, ServerAction.STOP)
        logger.info('Auto stop: stopped idle server %s (%s)', name, server_id)
        return True
