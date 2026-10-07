import unittest

from core.config import DEFAULT_AUTO_STOP_INTERVAL, ConfigError, Settings

REQUIRED = {'SERVER_URL': 'https://crafty.local:8443/', 'DISCORD_TOKEN': 'discord-secret',
            'CRAFTY_TOKEN': 'crafty-secret'}


class TestSettingsFromEnv(unittest.TestCase):

    def test_required_vars_and_defaults(self):
        settings = Settings.from_env(REQUIRED)
        self.assertEqual(settings.server_url, 'https://crafty.local:8443')
        self.assertEqual(settings.discord_token, 'discord-secret')
        self.assertEqual(settings.crafty_token, 'crafty-secret')
        self.assertIsNone(settings.guild_id)
        self.assertFalse(settings.auto_stop_enabled)
        self.assertEqual(settings.auto_stop_interval, DEFAULT_AUTO_STOP_INTERVAL)
        self.assertFalse(settings.verify_ssl)
        self.assertEqual(settings.log_level, 'INFO')
        self.assertIsNone(settings.log_file)
        self.assertEqual(settings.flags_file, 'data/feature_flags.json')

    def test_optional_vars(self):
        settings = Settings.from_env({**REQUIRED, 'GUILD_ID': '42', 'ENABLE_AUTO_STOP_SERVER': 'true',
                                      'AUTO_STOP_SLEEP_TIME': '60', 'CRAFTY_VERIFY_SSL': 'yes',
                                      'LOG_LEVEL': 'debug', 'LOG_FILE': 'logs/bot.log'})
        self.assertEqual(settings.guild_id, 42)
        self.assertTrue(settings.auto_stop_enabled)
        self.assertEqual(settings.auto_stop_interval, 60)
        self.assertTrue(settings.verify_ssl)
        self.assertEqual(settings.log_level, 'DEBUG')
        self.assertEqual(settings.log_file, 'logs/bot.log')

    def test_missing_all_vars(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({})

    def test_missing_or_empty_required_var(self):
        for name in REQUIRED:
            for value in (None, '', '  '):
                env = {k: v for k, v in REQUIRED.items() if k != name}
                if value is not None:
                    env[name] = value
                with self.subTest(name=name, value=value), self.assertRaises(ConfigError) as cm:
                    Settings.from_env(env)
                self.assertIn(name, str(cm.exception))

    def test_credentials_instead_of_token(self):
        env = {**REQUIRED, 'CRAFTY_TOKEN': '', 'CRAFTY_USERNAME': 'bot', 'CRAFTY_PASSWORD': 'secret'}
        settings = Settings.from_env(env)
        self.assertEqual(settings.crafty_token, '')
        self.assertEqual(settings.crafty_username, 'bot')
        self.assertEqual(settings.crafty_password, 'secret')

    def test_legacy_credential_names(self):
        env = {**REQUIRED, 'CRAFTY_TOKEN': '', 'USERNAME': 'bot', 'PASSWORD': 'secret'}
        self.assertEqual(Settings.from_env(env).crafty_username, 'bot')

    def test_incomplete_credentials(self):
        env = {**REQUIRED, 'CRAFTY_TOKEN': '', 'CRAFTY_USERNAME': 'bot', 'CRAFTY_PASSWORD': ''}
        with self.assertRaises(ConfigError):
            Settings.from_env(env)

    def test_invalid_values(self):
        for name, value in (('GUILD_ID', 'abc'), ('AUTO_STOP_SLEEP_TIME', '0'),
                            ('AUTO_STOP_SLEEP_TIME', 'x'), ('LOG_LEVEL', 'LOUD'), ('WEB_PORT', '0'),
                            ('WEB_PORT', '70000')):
            with self.subTest(name=name, value=value), self.assertRaises(ConfigError):
                Settings.from_env({**REQUIRED, name: value})

    def test_secrets_not_in_repr(self):
        text = repr(Settings.from_env({**REQUIRED, 'CRAFTY_PASSWORD': 'pw-secret', 'WEB_PASSWORD': 'web-secret'}))
        for secret in ('discord-secret', 'crafty-secret', 'pw-secret', 'web-secret'):
            self.assertNotIn(secret, text)

    def test_web_settings(self):
        defaults = Settings.from_env(REQUIRED)
        self.assertFalse(defaults.web_enabled)
        self.assertEqual((defaults.web_host, defaults.web_port, defaults.web_password), ('127.0.0.1', 8080, ''))
        settings = Settings.from_env({**REQUIRED, 'WEB_ENABLED': 'true', 'WEB_HOST': '0.0.0.0', 'WEB_PORT': '9000',
                                      'WEB_PASSWORD': 'pw'})
        self.assertTrue(settings.web_enabled)
        self.assertEqual((settings.web_host, settings.web_port, settings.web_password), ('0.0.0.0', 9000, 'pw'))


if __name__ == '__main__':
    unittest.main()
