"""
The Discord bot: wires the Crafty client, the cogs and the error handling together.
"""

from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core import __version__
from core.cogs.admin import AdminCommands
from core.cogs.auto_stop import AutoStop
from core.cogs.servers import ServerCommands
from core.config import Settings
from core.crafty import CraftyAPIError, CraftyClient
from core.help_command import HelpCommand

logger = logging.getLogger(__name__)

COMMAND_PREFIX = '>'

_WRAPPER_ERRORS = (commands.CommandInvokeError, commands.HybridCommandError,
                   app_commands.CommandInvokeError)


def unwrap_error(error: BaseException) -> BaseException:
    """Return the exception that was raised inside a command."""
    while isinstance(error, _WRAPPER_ERRORS):
        error = error.original
    return error


class CraftyBot(commands.Bot):
    """Discord bot that controls Crafty Controller servers."""

    def __init__(self, settings: Settings, crafty: CraftyClient):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents, help_command=HelpCommand())
        self.settings = settings
        self.crafty = crafty

    @property
    def guild(self) -> Optional[discord.Object]:
        """The guild the slash commands are registered for, or None for global commands."""
        if self.settings.guild_id is None:
            return None
        return discord.Object(id=self.settings.guild_id)

    async def setup_hook(self) -> None:
        if not self.settings.crafty_token:
            logger.info('No CRAFTY_TOKEN set, logging in with username and password')
            await self.crafty.login(self.settings.crafty_username, self.settings.crafty_password)

        await self.add_cog(ServerCommands(self.crafty))
        await self.add_cog(AdminCommands(self))
        if self.settings.auto_stop_enabled:
            await self.add_cog(AutoStop(self.crafty, self.settings.auto_stop_interval))
            logger.info('Auto stop enabled (every %d seconds)', self.settings.auto_stop_interval)
        else:
            logger.info('Auto stop disabled')

        if self.guild is not None:
            self.tree.copy_global_to(guild=self.guild)

    async def on_ready(self) -> None:
        logger.info('Bot is ready: %s', self.user)
        logger.info('Crafty Bot version %s', __version__)
        logger.debug('Server URL: %s, guild ID: %s', self.settings.server_url, self.settings.guild_id)

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError,
                               /) -> None:
        error = unwrap_error(exception)
        if isinstance(error, commands.CommandNotFound):
            await context.send(f'Command not found. Use `{COMMAND_PREFIX}help` to get a list of '
                               'available commands.')
        elif isinstance(error, commands.MissingRequiredArgument):
            await context.send(f'Missing required argument. Use `{COMMAND_PREFIX}help` to get a list '
                               'of available commands.')
        elif isinstance(error, commands.BadArgument):
            await context.send(str(error))
        elif isinstance(error, commands.CheckFailure):
            await context.send('You are not allowed to use this command.')
        elif isinstance(error, CraftyAPIError):
            logger.warning('Command %s failed: %s', context.command, error)
            await context.send('Request to Crafty Controller failed. Check the bot logs for details.')
        else:
            logger.error('Unexpected error in command %s', context.command, exc_info=error)
            await context.send('An unexpected error occurred.')
            return
        logger.debug('Command error: %s', error)

    async def close(self) -> None:
        await super().close()
        self.crafty.close()
