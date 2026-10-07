import os
import unittest
from unittest.mock import patch

import discord

from core import main


class TestMain(unittest.TestCase):

    @patch.object(main, 'setup_logging')
    @patch.object(main, 'load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_config_exits_with_error(self, _load_dotenv, _setup_logging):
        with self.assertLogs('core', level='ERROR'):
            self.assertEqual(main.main(), 1)

    @patch.object(main, 'setup_logging')
    @patch.object(main, 'CraftyBot')
    @patch.object(main, 'load_dotenv')
    @patch.dict(os.environ, {'SERVER_URL': 'https://crafty.local', 'DISCORD_TOKEN': 'discord',
                             'CRAFTY_TOKEN': 'crafty', 'LOG_LEVEL': 'debug', 'LOG_FILE': 'bot.log'}, clear=True)
    def test_runs_bot(self, _load_dotenv, bot_class, setup_logging):
        with self.assertLogs('core', level='DEBUG') as logs:
            self.assertEqual(main.main(), 0)
        bot_class.return_value.run.assert_called_once_with('discord', log_handler=None)
        setup_logging.assert_called_with('DEBUG', 'bot.log')
        self.assertNotIn('discord', ' '.join(record.getMessage() for record in logs.records
                                             if 'Settings' in record.getMessage()))

    @patch.object(main, 'setup_logging', side_effect=[None, OSError('read-only')])
    @patch.object(main, 'CraftyBot')
    @patch.object(main, 'load_dotenv')
    @patch.dict(os.environ, {'SERVER_URL': 'https://crafty.local', 'DISCORD_TOKEN': 'discord',
                             'CRAFTY_TOKEN': 'crafty', 'LOG_FILE': '/bot.log'}, clear=True)
    def test_unwritable_log_file_exits_with_error(self, _load_dotenv, bot_class, _setup_logging):
        with self.assertLogs('core', level='ERROR'):
            self.assertEqual(main.main(), 1)
        bot_class.assert_not_called()

    @patch.object(main, 'setup_logging')
    @patch.object(main, 'CraftyBot')
    @patch.object(main, 'load_dotenv')
    @patch.dict(os.environ, {'SERVER_URL': 'https://crafty.local', 'DISCORD_TOKEN': 'invalid',
                             'CRAFTY_TOKEN': 'crafty'}, clear=True)
    def test_invalid_discord_token_exits_with_error(self, _load_dotenv, bot_class, _setup_logging):
        bot_class.return_value.run.side_effect = discord.LoginFailure('Improper token has been passed.')
        with self.assertLogs('core', level='ERROR') as logs:
            self.assertEqual(main.main(), 1)
        self.assertIn('DISCORD_TOKEN', logs.output[-1])


if __name__ == '__main__':
    unittest.main()
