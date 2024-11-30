import asyncio
import os
import unittest
from unittest.mock import patch

from core.helper import check_env_vars, check_server_id


class TestCheckEnvVars(unittest.TestCase):
    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': 'token', 'CRAFTY_TOKEN': 'token'})
    def test_all_env_vars_set(self):
        check_env_vars()
        self.assertTrue(True)  # If no exception, the test passes

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_all_env_vars(self):
        with self.assertRaises(SystemExit):
            check_env_vars()


class TestCheckMissingEnvVars(unittest.TestCase):
    @patch.dict(os.environ, {'DISCORD_TOKEN': 'token', 'CRAFTY_TOKEN': 'token'})
    def test_missing_server_url(self):
        with self.assertRaises(SystemExit):
            check_env_vars()

    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': 'token'})
    def test_missing_crafty_token_and_missing_credentials(self):
        with self.assertRaises(SystemExit):
            check_env_vars()

    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': 'token',
                             'USERNAME': 'user', 'PASSWORD': 'pass'})
    def test_missing_crafty_token_but_has_credentials(self):
        with self.assertRaises(SystemExit):
            check_env_vars()  # If no exception, the test passes


class TestCheckEmptyEnvVars(unittest.TestCase):
    @patch.dict(os.environ, {'SERVER_URL': '', 'DISCORD_TOKEN': 'token', 'CRAFTY_TOKEN': 'token'})
    def test_empty_server_url(self):
        with self.assertRaises(SystemExit):
            check_env_vars()

    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': '', 'CRAFTY_TOKEN': 'token'})
    def test_empty_discord_token(self):
        with self.assertRaises(SystemExit):
            check_env_vars()

    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': 'token', 'CRAFTY_TOKEN': ''})
    def test_empty_crafty_token(self):
        with self.assertRaises(SystemExit):
            check_env_vars()

    @patch.dict(os.environ,
                {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': 'token', 'CRAFTY_TOKEN': '', 'USERNAME': '',
                 'PASSWORD': ''})
    def test_empty_crafty_token_and_empty_credentials(self):
        with self.assertRaises(SystemExit):
            check_env_vars()

    @patch.dict(os.environ,
                {'SERVER_URL': 'http://example.com', 'DISCORD_TOKEN': 'token', 'CRAFTY_TOKEN': '', 'USERNAME': 'Bla',
                 'PASSWORD': ''})
    def test_empty_crafty_token_and_empty_password(self):
        with self.assertRaises(SystemExit):
            check_env_vars()


class TestCheckServerId(unittest.TestCase):
    def test_valid_server_id(self):
        self.assertTrue(check_server_id('ff231030-910c-4aaa-bd83-50e03aedab1c'))

    def test_invalid_server_id(self):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(check_server_id('abc'))
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
