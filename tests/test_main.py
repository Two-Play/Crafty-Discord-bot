import os
import unittest
from unittest.mock import patch

from core import main


class TestMain(unittest.TestCase):

    @patch.object(main, 'load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_config_exits_with_error(self, _load_dotenv):
        with self.assertLogs('core', level='ERROR'):
            self.assertEqual(main.main(), 1)

    @patch.object(main, 'CraftyBot')
    @patch.object(main, 'load_dotenv')
    @patch.dict(os.environ, {'SERVER_URL': 'https://crafty.local', 'DISCORD_TOKEN': 'discord',
                             'CRAFTY_TOKEN': 'crafty'}, clear=True)
    def test_runs_bot(self, _load_dotenv, bot_class):
        self.assertEqual(main.main(), 0)
        bot_class.return_value.run.assert_called_once_with('discord', log_handler=None)


if __name__ == '__main__':
    unittest.main()
