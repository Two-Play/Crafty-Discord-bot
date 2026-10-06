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

        for server in servers:
            server_id = server['server_id']
            try:
                stats = await self._client.get_stats(server_id)
                if stats.get('running') and stats.get('online', 0) == 0:
                    await self._client.run_action(server_id, ServerAction.STOP)
                    logger.info('Auto stop: stopped idle server %s', server_id)
            except CraftyAPIError as exc:
                logger.warning('Auto stop failed for server %s: %s', server_id, exc)
