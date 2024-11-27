from discord.ext import commands


class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        ctx = self.context
        help_text = "Available commands:\n"
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            if filtered:
                for command in filtered:
                    help_text += f"```{self.get_command_signature(command)}```\t {command.description}\n"
        await ctx.send(help_text)

    async def send_command_help(self, command):
        ctx = self.context
        help_text = f"{self.get_command_signature(command)}\n\t{command.description}"
        await ctx.send(help_text)
