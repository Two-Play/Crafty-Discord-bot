"""
Background task that stops servers without players.
"""

import logging

from discord.ext import commands, tasks

from core.crafty import CraftyAPIError, CraftyClient, ServerAction

logger = logging.getLogger(__name__)


class AutoStop(commands.Cog):
    """Periodically stops every running server that has no players online."""

    def __init__(self, client: CraftyClient, interval: int):
        self._client = client
        self.stop_idle_servers.change_interval(seconds=interval)

    async def cog_load(self) -> None:
        self.stop_idle_servers.start()
        logger.info('Auto stop started, checking every %d seconds', self.stop_idle_servers.seconds)

    async def cog_unload(self) -> None:
        self.stop_idle_servers.cancel()

    @tasks.loop(minutes=30)
    async def stop_idle_servers(self) -> None:
        """Stop running servers without players. Errors are logged and retried next run."""
        try:
            servers = await self._client.list_servers()
        except CraftyAPIError as exc:
            logger.warning('Auto stop could not load the server list: %s', exc)
            return

        stopped = 0
        for server in servers:
            server_id = server.get('server_id')
            name = server.get('server_name') or server_id
            try:
                stats = await self._client.get_stats(server_id)
                if stats.get('running') and stats.get('online', 0) == 0:
                    await self._client.run_action(server_id, ServerAction.STOP)
                    stopped += 1
                    logger.info('Auto stop: stopped idle server %s (%s)', name, server_id)
            except CraftyAPIError as exc:
                logger.warning('Auto stop failed for server %s (%s): %s', name, server_id, exc)
            except Exception:  # pylint: disable=broad-exception-caught
                # An unexpected error must not end the loop, which would disable auto stop for good.
                logger.exception('Unexpected error in auto stop for server %s (%s)', name, server_id)
        logger.debug('Auto stop checked %d server(s), stopped %d', len(servers), stopped)
