import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.flags import FeatureFlags, FlagError, FlagSaveError, flag_definitions


class TestFeatureFlags(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.path = Path(self.directory.name) / 'data' / 'flags.json'

    def tearDown(self):
        self.directory.cleanup()

    def make(self, auto_stop_default=False):
        return FeatureFlags(flag_definitions(auto_stop_default), str(self.path))

    def test_defaults(self):
        flags = self.make()
        self.assertFalse(flags.is_enabled('auto_stop'))
        self.assertTrue(flags.is_enabled('command_start'))
        self.assertTrue(self.make(auto_stop_default=True).is_enabled('auto_stop'))
        self.assertTrue(flags.is_enabled('unknown'))

    def test_set_saves_and_reloads(self):
        self.make().set('command_stop', False)
        self.assertEqual(json.loads(self.path.read_text()), {'command_stop': False})
        self.assertFalse(self.make().is_enabled('command_stop'))

    def test_setting_the_default_removes_the_override(self):
        flags = self.make()
        flags.set('command_stop', False)
        flags.set('command_stop', True)
        self.assertEqual(json.loads(self.path.read_text()), {})

    def test_invalid_changes(self):
        flags = self.make()
        with self.assertRaises(FlagError):
            flags.set('nope', True)
        with self.assertRaises(FlagError):
            flags.set('command_stop', 'false')
        self.assertTrue(flags.is_enabled('command_stop'))

    def test_save_error_keeps_the_old_value(self):
        flags = self.make()
        with patch('core.flags.os.replace', side_effect=PermissionError('read-only')), \
                self.assertRaises(FlagSaveError):
            flags.set('command_stop', False)
        self.assertTrue(flags.is_enabled('command_stop'))
        self.assertEqual([name for name in os.listdir(self.path.parent) if name.startswith('.flags-')], [])

    def test_broken_file_uses_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{not json')
        with self.assertLogs('core.flags', level='ERROR'):
            flags = self.make()
        self.assertTrue(flags.is_enabled('command_stop'))

    def test_invalid_entries_are_ignored(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({'command_stop': False, 'nope': True, 'command_start': 'no'}))
        with self.assertLogs('core.flags', level='WARNING'):
            flags = self.make()
        self.assertFalse(flags.is_enabled('command_stop'))
        self.assertTrue(flags.is_enabled('command_start'))

    def test_no_file(self):
        flags = FeatureFlags(flag_definitions(), None)
        flags.set('command_stop', False)
        self.assertFalse(flags.is_enabled('command_stop'))

    def test_as_list(self):
        names = [flag['name'] for flag in self.make().as_list()]
        self.assertEqual(names[0], 'auto_stop')
        self.assertIn('command_backup', names)


if __name__ == '__main__':
    unittest.main()
