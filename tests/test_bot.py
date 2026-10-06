import unittest
from unittest.mock import AsyncMock, MagicMock

from discord.ext import commands

from core.bot import CraftyBot, unwrap_error
from core.config import Settings
from core.crafty import CraftyAPIError

SETTINGS = Settings(server_url='https://crafty.local', discord_token='discord', crafty_token='crafty')


class TestUnwrapError(unittest.TestCase):

    def test_unwraps_invoke_error(self):
        original = CraftyAPIError('down')
        self.assertIs(unwrap_error(commands.CommandInvokeError(original)), original)

    def test_keeps_other_errors(self):
        error = commands.BadArgument('bad')
        self.assertIs(unwrap_error(error), error)


class TestCraftyBot(unittest.IsolatedAsyncioTestCase):

    def make_bot(self, **settings):
        self.crafty = MagicMock()
        self.crafty.login = AsyncMock()
        fields = {**SETTINGS.__dict__, **settings}
        return CraftyBot(Settings(**fields), self.crafty)

    async def test_setup_registers_cogs(self):
        bot = self.make_bot()
        await bot.setup_hook()
        self.assertIsNotNone(bot.get_cog('Servers'))
        self.assertIsNotNone(bot.get_cog('Admin'))
        self.assertIsNone(bot.get_cog('AutoStop'))
        self.crafty.login.assert_not_awaited()

    async def test_setup_logs_in_without_token(self):
        bot = self.make_bot(crafty_token='', crafty_username='user', crafty_password='pw')
        await bot.setup_hook()
        self.crafty.login.assert_awaited_once_with('user', 'pw')

    async def test_setup_copies_commands_to_guild(self):
        bot = self.make_bot(guild_id=123)
        await bot.setup_hook()
        names = {command.name for command in bot.tree.get_commands(guild=bot.guild)}
        self.assertIn('start', names)

    async def test_error_messages(self):
        bot = self.make_bot()
        cases = [
            (commands.CommandNotFound(), 'Command not found'),
            (commands.MissingRequiredArgument(MagicMock()), 'Missing required argument'),
            (commands.BadArgument('Invalid server ID'), 'Invalid server ID'),
            (commands.NotOwner(), 'not allowed'),
            (commands.CommandInvokeError(CraftyAPIError('down')), 'Crafty Controller failed'),
            (commands.CommandInvokeError(RuntimeError('boom')), 'unexpected error'),
        ]
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                ctx = MagicMock()
                ctx.send = AsyncMock()
                with self.assertLogs('core.bot', level='DEBUG'):
                    await bot.on_command_error(ctx, error)
                self.assertIn(expected, ctx.send.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
