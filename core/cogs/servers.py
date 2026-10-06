"""
Commands to list, inspect, start, stop and restart Crafty servers.
"""

from __future__ import annotations

import logging
import time
from typing import List

from discord import Interaction, app_commands
from discord.ext import commands

from core.crafty import CraftyAPIError, CraftyClient, JsonDict, ServerAction, parse_server_id
from core.formatting import format_server_list, format_server_stats

logger = logging.getLogger(__name__)

SERVER_LIST_CACHE_TTL = 60  # seconds
MAX_AUTOCOMPLETE_CHOICES = 25  # Discord limit


class ServerId(commands.Converter):
    """Converts the argument to a canonical server ID or rejects it."""

    async def convert(self, ctx: commands.Context, argument: str) -> str:  # pylint: disable=unused-argument
        server_id = parse_server_id(argument)
        if server_id is None:
            raise commands.BadArgument('Invalid server ID. Use `>list` to get the server IDs.')
        return server_id


class ServerCommands(commands.Cog, name='Servers'):
    """Commands to control the Crafty servers."""

    def __init__(self, client: CraftyClient):
        self._client = client
        self._server_cache: List[JsonDict] = []
        self._server_cache_time = 0.0

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        # Crafty requests can take longer than the 3 seconds Discord grants to answer an interaction.
        await ctx.defer()

    async def _cached_servers(self) -> List[JsonDict]:
        now = time.monotonic()
        if not self._server_cache or now - self._server_cache_time >= SERVER_LIST_CACHE_TTL:
            self._server_cache = await self._client.list_servers()
            self._server_cache_time = now
        return self._server_cache

    async def server_autocomplete(self, _interaction: Interaction,
                                  current: str) -> List[app_commands.Choice[str]]:
        """Suggest servers whose name starts with the typed text."""
        try:
            servers = await self._cached_servers()
        except CraftyAPIError as exc:
            logger.warning('Autocomplete could not load the server list: %s', exc)
            return []

        current = current.lower()
        choices = [
            app_commands.Choice(name=server.get('server_name') or server['server_id'],
                                value=server['server_id'])
            for server in servers
            if str(server.get('server_name', '')).lower().startswith(current)
        ]
        return choices[:MAX_AUTOCOMPLETE_CHOICES]

    async def _ensure_stoppable(self, ctx: commands.Context, server_id: str, verb: str) -> bool:
        """Reply and return False if the server is not running or players are online."""
        stats = await self._client.get_stats(server_id)
        if not stats.get('running'):
            await ctx.reply('Server already stopped')
            return False

        player_count = stats.get('online', 0)
        if player_count:
            await ctx.reply(f'cannot {verb} server: {player_count} Player(s) online')
            return False
        return True

    @commands.hybrid_command(name='list', description='get server list')
    async def list_servers(self, ctx: commands.Context) -> None:
        """List all servers with their IDs."""
        servers = await self._client.list_servers()
        await ctx.reply(f'Server information:\n{format_server_list(servers)}')

    @commands.hybrid_command(name='stats', description='get server stats')
    @app_commands.autocomplete(server_id=server_autocomplete)
    async def stats(self, ctx: commands.Context, server_id: ServerId) -> None:
        """Show the statistics of a server."""
        stats = await self._client.get_stats(server_id)
        await ctx.reply(f'Server information:\n{format_server_stats(stats)}')

    @commands.hybrid_command(name='start', description='start a server')
    @app_commands.autocomplete(server_id=server_autocomplete)
    async def start(self, ctx: commands.Context, server_id: ServerId) -> None:
        """Start a server."""
        stats = await self._client.get_stats(server_id)
        if stats.get('running'):
            await ctx.reply('Server already running')
            return

        await self._client.run_action(server_id, ServerAction.START)
        logger.info('Server %s started by %s', server_id, ctx.author)
        await ctx.reply('Server started')

    @commands.hybrid_command(name='stop', description='stop a server')
    @app_commands.autocomplete(server_id=server_autocomplete)
    async def stop(self, ctx: commands.Context, server_id: ServerId) -> None:
        """Stop a server if no players are online."""
        if not await self._ensure_stoppable(ctx, server_id, 'stop'):
            return

        await self._client.run_action(server_id, ServerAction.STOP)
        logger.info('Server %s stopped by %s', server_id, ctx.author)
        await ctx.reply('Server stopped')

    @commands.hybrid_command(name='restart', description='restart a server')
    @app_commands.autocomplete(server_id=server_autocomplete)
    async def restart(self, ctx: commands.Context, server_id: ServerId) -> None:
        """Restart a running server if no players are online."""
        if not await self._ensure_stoppable(ctx, server_id, 'restart'):
            return

        await self._client.run_action(server_id, ServerAction.RESTART)
        logger.info('Server %s restarted by %s', server_id, ctx.author)
        await ctx.reply('Server restarted')
