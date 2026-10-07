"""
Commands to list, inspect, start, stop and restart Crafty servers.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from discord import Interaction, app_commands
from discord.ext import commands

from core.crafty import (CraftyAPIError, CraftyClient, JsonDict, ServerAction, busy_state, parse_server_id,
                         player_count)
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


def select_backup(backups: List[JsonDict], name: Optional[str]) -> Optional[JsonDict]:
    """
    Pick the backup configuration by name or ID. Without a name, pick the default
    configuration, or the only one if there is just one.
    """
    if name:
        wanted = name.strip().lower()
        for backup in backups:
            if wanted in (str(backup.get('backup_name', '')).lower(), str(backup.get('backup_id', '')).lower()):
                return backup
        return None
    for backup in backups:
        if backup.get('default'):
            return backup
    return backups[0] if len(backups) == 1 else None


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
            logger.debug('Server list cache refreshed (%d servers)', len(self._server_cache))
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

    async def backup_autocomplete(self, interaction: Interaction,
                                  current: str) -> List[app_commands.Choice[str]]:
        """Suggest the backup configurations of the server selected in the same command."""
        server_id = parse_server_id(str(getattr(interaction.namespace, 'server_id', '') or ''))
        if server_id is None:
            return []
        try:
            backups = await self._client.list_backups(server_id)
        except CraftyAPIError as exc:
            logger.warning('Autocomplete could not load the backups of server %s: %s', server_id, exc)
            return []

        current = current.lower()
        names = [str(backup.get('backup_name') or backup['backup_id']) for backup in backups]
        return [app_commands.Choice(name=name, value=name)
                for name in names if name.lower().startswith(current)][:MAX_AUTOCOMPLETE_CHOICES]

    async def _ensure_stoppable(self, ctx: commands.Context, server_id: str, verb: str) -> bool:
        """Reply and return False if the server is not running or players are online."""
        stats = await self._client.get_stats(server_id)
        if not stats.get('running'):
            await ctx.reply('Server already stopped')
            return False

        players = player_count(stats)
        if players:
            await ctx.reply(f'cannot {verb} server: {players} Player(s) online')
            return False
        if players is None:
            # Without a working ping the player count is unknown. Don't block the command, since
            # some servers never answer pings, but leave a trace in case players were kicked.
            logger.warning('Player count of server %s is unknown, %s it anyway', server_id, verb)
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
        state = busy_state(stats)
        if state:
            await ctx.reply(f'Server is already {state}')
            return

        await self._client.run_action(server_id, ServerAction.START)
        logger.info('Server %s started by %s (%s)', server_id, ctx.author, ctx.author.id)
        await ctx.reply('Server started')

    @commands.hybrid_command(name='stop', description='stop a server')
    @app_commands.autocomplete(server_id=server_autocomplete)
    async def stop(self, ctx: commands.Context, server_id: ServerId) -> None:
        """Stop a server if no players are online."""
        if not await self._ensure_stoppable(ctx, server_id, 'stop'):
            return

        await self._client.run_action(server_id, ServerAction.STOP)
        logger.info('Server %s stopped by %s (%s)', server_id, ctx.author, ctx.author.id)
        await ctx.reply('Server stopped')

    @commands.hybrid_command(name='restart', description='restart a server')
    @app_commands.autocomplete(server_id=server_autocomplete)
    async def restart(self, ctx: commands.Context, server_id: ServerId) -> None:
        """Restart a running server if no players are online."""
        if not await self._ensure_stoppable(ctx, server_id, 'restart'):
            return

        await self._client.run_action(server_id, ServerAction.RESTART)
        logger.info('Server %s restarted by %s (%s)', server_id, ctx.author, ctx.author.id)
        await ctx.reply('Server restarted')

    @commands.hybrid_command(name='backup', description='create a backup of a server (owner only)')
    @commands.is_owner()
    @app_commands.autocomplete(server_id=server_autocomplete, backup=backup_autocomplete)
    async def backup(self, ctx: commands.Context, server_id: ServerId, *, backup: Optional[str] = None) -> None:
        """Start a backup of a server. Without a backup name the default backup configuration is used."""
        backups = await self._client.list_backups(server_id)
        if not backups:
            await ctx.reply('No backup configured for this server. Create one in Crafty first.')
            return

        selected = select_backup(backups, backup)
        if selected is None:
            names = ', '.join(f"`{entry.get('backup_name') or entry['backup_id']}`" for entry in backups)
            prefix = f'Backup `{backup}` not found' if backup else 'No default backup configured'
            await ctx.reply(f'{prefix}. Available backups: {names}')
            return

        name = selected.get('backup_name') or selected['backup_id']
        await self._client.run_backup(server_id, selected['backup_id'])
        logger.info('Backup %s (%s) of server %s started by %s (%s)', name, selected['backup_id'], server_id,
                    ctx.author, ctx.author.id)
        await ctx.reply(f'Backup `{name}` started. Crafty runs it in the background.')
