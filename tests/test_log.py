import io
import logging
import logging.handlers
import os
import tempfile
import unittest
from contextlib import redirect_stderr

from core.log import setup_logging


class TestSetupLogging(unittest.TestCase):

    def setUp(self):
        root = logging.getLogger()
        self.saved = (root.handlers[:], root.level, logging.getLogger('core').level)
        root.handlers = []

    def tearDown(self):
        root = logging.getLogger()
        for handler in root.handlers:
            handler.close()
        root.handlers, root.level = self.saved[0], self.saved[1]
        logging.getLogger('core').setLevel(self.saved[2])

    def test_debug_only_for_bot_loggers(self):
        setup_logging('debug')
        self.assertEqual(logging.getLogger('core').level, logging.DEBUG)
        self.assertEqual(logging.getLogger().level, logging.INFO)
        self.assertFalse(logging.getLogger('discord.gateway').isEnabledFor(logging.DEBUG))
        self.assertTrue(logging.getLogger('core.crafty').isEnabledFor(logging.DEBUG))

    def test_higher_level_applies_to_everything(self):
        setup_logging(logging.WARNING)
        self.assertFalse(logging.getLogger('discord').isEnabledFor(logging.INFO))
        self.assertFalse(logging.getLogger('core.bot').isEnabledFor(logging.INFO))

    def test_reconfigure_replaces_handlers(self):
        setup_logging()
        setup_logging()
        self.assertEqual(len(logging.getLogger().handlers), 1)

    def test_log_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'logs', 'bot.log')
            with redirect_stderr(io.StringIO()):
                setup_logging('INFO', path)
            logging.getLogger('core.test').info('hello file')
            for handler in logging.getLogger().handlers:
                handler.flush()
            handlers = logging.getLogger().handlers
            self.assertTrue(any(isinstance(h, logging.handlers.RotatingFileHandler) for h in handlers))
            with open(path, encoding='utf-8') as file:
                self.assertIn('hello file', file.read())
            setup_logging()  # close the file handler before the directory is removed


if __name__ == '__main__':
    unittest.main()
