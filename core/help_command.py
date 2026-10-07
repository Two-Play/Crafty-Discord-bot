"""
Compact help command that lists every command with its description.
"""

from discord.ext import commands


class HelpCommand(commands.HelpCommand):
    """Help command that shows each command signature in a code block."""

    # pylint: disable=arguments-differ  # the base methods use positional-only parameters

    async def send_bot_help(self, mapping, /):
        help_text = 'Available commands:\n'
        for cog_commands in mapping.values():
            for command in await self.filter_commands(cog_commands, sort=True):
                help_text += f'```{self.get_command_signature(command)}```\t {command.description}\n'
        await self.get_destination().send(help_text)

    async def send_command_help(self, command, /):
        help_text = f'{self.get_command_signature(command)}\n\t{command.description}'
        await self.get_destination().send(help_text)
