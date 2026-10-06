import unittest
from unittest.mock import AsyncMock, MagicMock

from core.help_command import HelpCommand


class TestHelpCommand(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.help_command = HelpCommand()
        self.destination = MagicMock()
        self.destination.send = AsyncMock()
        self.help_command.get_destination = MagicMock(return_value=self.destination)
        self.help_command.get_command_signature = lambda command: f'>{command.name}'
        self.command = MagicMock()
        self.command.name = 'start'
        self.command.description = 'start a server'

    async def test_bot_help_lists_commands(self):
        self.help_command.filter_commands = AsyncMock(side_effect=lambda commands, sort: commands)
        await self.help_command.send_bot_help({None: [self.command]})
        self.assertIn('```>start```\t start a server', self.destination.send.call_args.args[0])

    async def test_command_help(self):
        await self.help_command.send_command_help(self.command)
        self.destination.send.assert_awaited_once_with('>start\n\tstart a server')


if __name__ == '__main__':
    unittest.main()
