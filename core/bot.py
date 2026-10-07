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
from core.web.dashboard import DashboardStartError, WebDashboard

logger = logging.getLogger(__name__)

COMMAND_PREFIX = '>'

_WRAPPER_ERRORS = (commands.CommandInvokeError, commands.HybridCommandError,
                   app_commands.CommandInvokeError)


def unwrap_error(error: BaseException) -> BaseException:
    """Return the exception that was raised inside a command."""
    while isinstance(error, _WRAPPER_ERRORS):
        error = error.original
    return error


def describe_context(ctx: commands.Context) -> str:
    """Describe who invoked a command where, for log messages."""
    author = ctx.author
    location = f'guild {ctx.guild.id}' if ctx.guild is not None else 'DM'
    kind = 'slash' if ctx.interaction is not None else 'prefix'
    return f'{author} ({author.id}) in {location} [{kind}]'


class CraftyBot(commands.Bot):
    """Discord bot that controls Crafty Controller servers."""

    def __init__(self, settings: Settings, crafty: CraftyClient):
        # The bot doesn't use voice, so the warnings about missing voice libraries are just noise.
        discord.VoiceClient.warn_nacl = False
        discord.VoiceClient.warn_dave = False
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
            logger.info('Logged in to Crafty as %s', self.settings.crafty_username)

        await self.add_cog(ServerCommands(self.crafty))
        await self.add_cog(AdminCommands(self))
        if self.settings.auto_stop_enabled:
            await self.add_cog(AutoStop(self.crafty, self.settings.auto_stop_interval))
            logger.info('Auto stop enabled (every %d seconds)', self.settings.auto_stop_interval)
        else:
            logger.info('Auto stop disabled')
        if self.settings.web_enabled:
            try:
                await self.add_cog(WebDashboard(self))
            except DashboardStartError as exc:
                # The dashboard is optional, so the bot keeps running without it.
                logger.error('%s. The bot keeps running without the dashboard.', exc)

        if self.guild is not None:
            self.tree.copy_global_to(guild=self.guild)
            logger.info('Slash commands registered for guild %s', self.settings.guild_id)
        else:
            logger.info('Slash commands registered globally')

    async def on_ready(self) -> None:
        # Also called after the bot reconnected to Discord.
        logger.info('Connected to Discord as %s (%s) in %d guild(s), Crafty Bot %s, Crafty at %s',
                    self.user, getattr(self.user, 'id', None), len(self.guilds), __version__,
                    self.settings.server_url)

    async def on_command(self, ctx: commands.Context) -> None:
        arguments = [arg for arg in ctx.args if not isinstance(arg, (commands.Cog, commands.Context))]
        logger.debug('%s invoked %s with %r %r', describe_context(ctx), ctx.command.qualified_name,
                     arguments, ctx.kwargs)

    async def on_command_completion(self, ctx: commands.Context) -> None:
        logger.debug('Command %s of %s completed', ctx.command.qualified_name, describe_context(ctx))

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError,
                               /) -> None:
        error = unwrap_error(exception)
        command = context.command.qualified_name if context.command else context.invoked_with
        origin = describe_context(context)
        if isinstance(error, commands.CommandNotFound):
            logger.debug('%s used unknown command %r', origin, context.invoked_with)
            await context.send(f'Command not found. Use `{COMMAND_PREFIX}help` to get a list of '
                               'available commands.')
        elif isinstance(error, commands.UserInputError):
            logger.debug('Invalid input for command %s from %s: %s', command, origin, error)
            if isinstance(error, commands.MissingRequiredArgument):
                await context.send(f'Missing required argument. Use `{COMMAND_PREFIX}help` to get a '
                                   'list of available commands.')
            else:
                await context.send(str(error))
        elif isinstance(error, commands.CheckFailure):
            logger.warning('%s is not allowed to use command %s: %s', origin, command,
                           error or type(error).__name__)
            await context.send('You are not allowed to use this command.')
        elif isinstance(error, CraftyAPIError):
            logger.warning('Command %s of %s failed: %s', command, origin, error)
            await context.send('Request to Crafty Controller failed. Check the bot logs for details.')
        else:
            logger.error('Unexpected error in command %s of %s', command, origin, exc_info=error)
            await context.send('An unexpected error occurred.')

    async def close(self) -> None:
        logger.info('Shutting down')
        await super().close()
        self.crafty.close()
