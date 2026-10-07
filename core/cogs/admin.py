"""
Owner-only commands to manage slash commands and the Crafty login.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import CraftyBot

logger = logging.getLogger(__name__)


class AdminCommands(commands.Cog, name='Admin'):
    """Commands only the bot owner can use."""

    def __init__(self, bot: CraftyBot):
        self.bot = bot

    @commands.hybrid_command(name='sync', description='Sync slash commands')
    @commands.is_owner()
    async def sync(self, ctx: commands.Context) -> None:
        """Sync the slash commands to the configured guild (or globally if none is set)."""
        guild = self.bot.guild
        if guild is not None:
            self.bot.tree.copy_global_to(guild=guild)
        synced = await self.bot.tree.sync(guild=guild)
        logger.info('%s synced %d slash commands %s', ctx.author, len(synced),
                    f'to guild {guild.id}' if guild is not None else 'globally')
        await ctx.reply(f'{len(synced)} commands synced')

    @commands.hybrid_command(name='clear', description='Clear all slash commands')
    @commands.is_owner()
    async def clear(self, ctx: commands.Context) -> None:
        """Remove the guild slash commands from the local command tree (run `sync` afterwards)."""
        self.bot.tree.clear_commands(guild=self.bot.guild)
        logger.info('%s cleared the slash commands from the local command tree', ctx.author)
        await ctx.reply('All commands cleared')

    @commands.hybrid_command(name='commands', description='Get all slash commands')
    @commands.is_owner()
    async def list_commands(self, ctx: commands.Context) -> None:
        """Show how many slash commands are registered for the guild."""
        registered = self.bot.tree.get_commands(guild=self.bot.guild)
        await ctx.reply(f'Got {len(registered)} commands')

    @commands.hybrid_command(name='get_token', description='get token if not set (not recommended)')
    @commands.is_owner()
    async def get_token(self, ctx: commands.Context) -> None:
        """Log in to Crafty with the configured username and password."""
        settings = self.bot.settings
        if not (settings.crafty_username and settings.crafty_password):
            await ctx.reply('CRAFTY_USERNAME and CRAFTY_PASSWORD are not set')
            return

        await self.bot.crafty.login(settings.crafty_username, settings.crafty_password)
        logger.info('%s retrieved a new Crafty token', ctx.author)
        await ctx.reply('Token successfully retrieved')
