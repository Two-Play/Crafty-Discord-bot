import socket
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from discord.ext import commands

from core.bot import CraftyBot, unwrap_error
from core.config import Settings
from core.crafty import CraftyAPIError
from core.flags import FeatureDisabled

SETTINGS = Settings(server_url='https://crafty.local', discord_token='discord', crafty_token='crafty',
                    flags_file='')


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
        self.assertFalse(bot.get_cog('AutoStop').enabled)
        self.crafty.login.assert_not_awaited()

    async def test_setup_loads_dashboard_when_enabled(self):
        bot = self.make_bot(web_enabled=True)
        with patch('core.bot.WebDashboard') as dashboard:
            dashboard.return_value = commands.Cog()
            await bot.setup_hook()
        dashboard.assert_called_once_with(bot)

    async def test_setup_continues_when_dashboard_port_is_in_use(self):
        with socket.socket() as blocker:
            blocker.bind(('127.0.0.1', 0))
            blocker.listen()
            bot = self.make_bot(web_enabled=True, web_port=blocker.getsockname()[1])
            with self.assertLogs('core.bot', level='ERROR') as logs:
                await bot.setup_hook()
        self.assertIn('already in use', logs.output[-1])
        self.assertIn('keeps running without the dashboard', logs.output[-1])
        self.assertIsNone(bot.get_cog('WebDashboard'))
        self.assertIsNotNone(bot.get_cog('Servers'))

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
            (FeatureDisabled('stop'), '`stop` command is currently disabled'),
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

    async def test_error_logs_contain_user(self):
        bot = self.make_bot()
        ctx = MagicMock()
        ctx.send = AsyncMock()
        ctx.author.__str__.return_value = 'alice'
        ctx.author.id = 7
        ctx.command.qualified_name = 'sync'
        with self.assertLogs('core.bot', level='WARNING') as logs:
            await bot.on_command_error(ctx, commands.NotOwner())
        self.assertIn('alice (7)', logs.output[0])
        self.assertIn('sync', logs.output[0])

    async def test_command_invocation_is_logged(self):
        bot = self.make_bot()
        ctx = MagicMock()
        ctx.guild = None
        ctx.interaction = None
        ctx.args = [MagicMock(spec=commands.Cog), MagicMock(spec=commands.Context), 'abc']
        ctx.kwargs = {}
        ctx.command.qualified_name = 'stats'
        with self.assertLogs('core.bot', level='DEBUG') as logs:
            await bot.on_command(ctx)
            await bot.on_command_completion(ctx)
        self.assertIn("stats with ['abc']", logs.output[0])
        self.assertIn('DM [prefix]', logs.output[0])
        self.assertIn('completed', logs.output[1])


if __name__ == '__main__':
    unittest.main()
