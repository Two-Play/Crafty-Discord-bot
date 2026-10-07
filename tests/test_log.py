import io
import logging
import logging.handlers
import os
import tempfile
import unittest
from contextlib import redirect_stderr

from core.log import LOG_BUFFER, LogBuffer, get_log_level, set_log_level, setup_logging


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
        handlers = logging.getLogger().handlers
        self.assertEqual(len(handlers), 2)
        self.assertIn(LOG_BUFFER, handlers)

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

    def test_set_and_get_log_level(self):
        setup_logging()
        set_log_level('warning')
        self.assertEqual(get_log_level(), 'WARNING')
        with self.assertRaises(ValueError):
            set_log_level('LOUD')


class TestLogBuffer(unittest.TestCase):

    def setUp(self):
        self.buffer = LogBuffer(capacity=3)
        self.logger = logging.getLogger('core.test.buffer')
        self.logger.addHandler(self.buffer)
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG)
        self.addCleanup(self.logger.removeHandler, self.buffer)
        self.addCleanup(setattr, self.logger, 'propagate', True)

    def test_keeps_the_newest_entries(self):
        for number in range(5):
            self.logger.info('entry %d', number)
        entries = self.buffer.entries()
        self.assertEqual([entry['message'] for entry in entries], ['entry 2', 'entry 3', 'entry 4'])
        self.assertEqual([entry['id'] for entry in entries], [3, 4, 5])
        self.assertEqual(entries[0]['logger'], 'core.test.buffer')

    def test_after_and_limit(self):
        for number in range(3):
            self.logger.info('entry %d', number)
        self.assertEqual([entry['id'] for entry in self.buffer.entries(after=1)], [2, 3])
        self.assertEqual([entry['id'] for entry in self.buffer.entries(limit=1)], [3])
        self.assertEqual(self.buffer.entries(limit=0), [])

    def test_exception_is_included(self):
        try:
            raise ValueError('broken')
        except ValueError:
            self.logger.exception('failed')
        message = self.buffer.entries()[-1]['message']
        self.assertTrue(message.startswith('failed\n'))
        self.assertIn('ValueError: broken', message)


if __name__ == '__main__':
    unittest.main()
