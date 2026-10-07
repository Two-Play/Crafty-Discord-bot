import base64
import errno
import logging
import math
import socket
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp.test_utils import TestClient, TestServer

from core.config import Settings
from core.crafty import CraftyAPIError
from core.flags import FeatureFlags, FlagSaveError, flag_definitions
from core.log import LOG_BUFFER, set_log_level
from core.web.dashboard import DashboardStartError, WebDashboard, describe_bind_error, summarize_server

SETTINGS = Settings(server_url='https://crafty.local', discord_token='discord', crafty_token='crafty',
                    web_enabled=True)

RUNNING_STATS = {'running': True, 'int_ping_results': 'True', 'online': 1, 'max': 10, 'players': "['Steve']",
                 'version': '1.21.4', 'cpu': 3.5, 'mem': 1073741824.0, 'mem_percent': 12.0}


def make_bot(settings=SETTINGS):
    bot = MagicMock()
    bot.settings = settings
    bot.flags = FeatureFlags(flag_definitions(settings.auto_stop_enabled), None)
    bot.latency = 0.042
    bot.guilds = [object()]
    bot.user = 'CraftyBot#0001'
    bot.is_ready.return_value = True
    bot.is_closed.return_value = False
    bot.crafty.list_servers = AsyncMock(return_value=[
        {'server_id': 'a', 'server_name': 'Survival', 'server_ip': '127.0.0.1', 'server_port': 25565},
        {'server_id': 'b', 'server_name': 'Creative'},
    ])
    bot.crafty.get_stats = AsyncMock(side_effect=lambda server_id: {
        'a': RUNNING_STATS,
        'b': {'running': False, 'int_ping_results': 'False', 'online': 0},
    }[server_id])
    return bot


class TestSummarizeServer(unittest.TestCase):

    def test_running(self):
        summary = summarize_server({'server_id': 'a', 'server_name': 'Survival'}, RUNNING_STATS)
        self.assertEqual(summary['players'], 1)
        self.assertEqual(summary['player_names'], ['Steve'])
        self.assertEqual(summary['memory'], '1.0 GB')
        self.assertIsNone(summary['state'])

    def test_stopped_hides_runtime_values(self):
        summary = summarize_server({'server_id': 'b'}, {'running': False, 'version': '1.21', 'cpu': 0})
        self.assertEqual(summary['name'], 'b')
        self.assertIsNone(summary['players'])
        self.assertIsNone(summary['version'])
        self.assertIsNone(summary['cpu'])


class DashboardTestCase(unittest.IsolatedAsyncioTestCase):

    settings = SETTINGS

    def setUp(self):
        # The dashboard reads the shared log buffer and changes the level of the 'core' logger.
        root = logging.getLogger()
        saved = (root.level, logging.getLogger('core').level, LOG_BUFFER in root.handlers)
        root.addHandler(LOG_BUFFER)
        set_log_level('INFO')

        def restore():
            root.setLevel(saved[0])
            logging.getLogger('core').setLevel(saved[1])
            if not saved[2]:
                root.removeHandler(LOG_BUFFER)
        self.addCleanup(restore)

    async def asyncSetUp(self):
        self.bot = make_bot(self.settings)
        self.dashboard = WebDashboard(self.bot)
        self.client = TestClient(TestServer(self.dashboard.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()


class TestDashboard(DashboardTestCase):

    async def test_status(self):
        response = await self.client.get('/api/status')
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertTrue(data['bot']['connected'])
        self.assertEqual(data['bot']['latency_ms'], 42)
        self.assertEqual([server['name'] for server in data['servers']], ['Survival', 'Creative'])
        self.assertEqual(data['servers'][0]['players'], 1)
        self.assertIsNone(data['error'])

    async def test_status_is_cached(self):
        await self.client.get('/api/status')
        await self.client.get('/api/status')
        self.bot.crafty.list_servers.assert_awaited_once()

    async def test_crafty_unreachable(self):
        self.bot.crafty.list_servers.side_effect = CraftyAPIError('down')
        with self.assertLogs('core.web.dashboard', level='WARNING'):
            data = await (await self.client.get('/api/status')).json()
        self.assertEqual(data['servers'], [])
        self.assertIn('not reachable', data['error'])

    async def test_stats_error_for_one_server(self):
        self.bot.crafty.get_stats.side_effect = lambda server_id: (
            RUNNING_STATS if server_id == 'a' else (_ for _ in ()).throw(CraftyAPIError('down')))
        with self.assertLogs('core.web.dashboard', level='WARNING'):
            data = await (await self.client.get('/api/status')).json()
        self.assertIsNone(data['servers'][0]['error'])
        self.assertEqual(data['servers'][1]['error'], 'Stats not available')

    async def test_latency_before_connect(self):
        self.bot.latency = math.inf
        data = await (await self.client.get('/api/status')).json()
        self.assertIsNone(data['bot']['latency_ms'])

    async def test_static_files_and_security_headers(self):
        for path, content_type in (('/', 'text/html'), ('/app.js', 'text/javascript'), ('/app.css', 'text/css')):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assertEqual(response.status, 200)
                self.assertEqual(response.content_type, content_type)
                self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')

    async def test_unexpected_error_returns_500(self):
        self.bot.crafty.list_servers.side_effect = RuntimeError('boom')
        with self.assertLogs('core.web.dashboard', level='ERROR'):
            response = await self.client.get('/api/status')
        self.assertEqual(response.status, 500)
        self.assertIn('Internal error', (await response.json())['error'])

    async def test_server_without_id_is_skipped(self):
        self.bot.crafty.list_servers.return_value = [{'server_name': 'broken'}, {'server_id': 'a'}]
        data = await (await self.client.get('/api/status')).json()
        self.assertEqual([server['id'] for server in data['servers']], ['a'])

    async def test_missing_static_file(self):
        with patch('core.web.dashboard.STATIC_DIR', Path('/nonexistent-crafty-bot-static')), \
                self.assertLogs('core.web.dashboard', level='ERROR'):
            response = await self.client.get('/app.js')
        self.assertEqual(response.status, 500)

    async def test_logs(self):
        logging.getLogger('core.test').info('first entry')
        data = await (await self.client.get('/api/logs')).json()
        entry = next(entry for entry in reversed(data['entries']) if entry['logger'] == 'core.test')
        self.assertEqual((entry['message'], entry['level']), ('first entry', 'INFO'))
        self.assertEqual(data['level'], 'INFO')
        self.assertEqual(data['levels'], ['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        self.assertFalse(data['editable'])

        last_id = entry['id']
        logging.getLogger('core.test').warning('second entry')
        data = await (await self.client.get(f'/api/logs?after={last_id}')).json()
        # The test server also writes an aiohttp access log, which the bot turns off.
        self.assertEqual([entry['message'] for entry in data['entries'] if entry['logger'] == 'core.test'],
                         ['second entry'])

    async def test_logs_invalid_after(self):
        response = await self.client.get('/api/logs?after=abc')
        self.assertEqual(response.status, 400)

    async def test_log_level_read_only_without_password(self):
        response = await self.client.put('/api/log-level', json={'level': 'DEBUG'}, headers={'X-Crafty-Bot': '1'})
        self.assertEqual(response.status, 403)

    async def test_flags_read_only_without_password(self):
        data = await (await self.client.get('/api/flags')).json()
        self.assertFalse(data['editable'])
        response = await self.client.put('/api/flags/command_stop', json={'enabled': False},
                                         headers={'X-Crafty-Bot': '1'})
        self.assertEqual(response.status, 403)
        self.assertTrue(self.bot.flags.is_enabled('command_stop'))

    async def test_health(self):
        response = await self.client.get('/healthz')
        self.assertEqual(await response.text(), 'ok')


class TestDashboardPassword(DashboardTestCase):

    settings = Settings(**{**SETTINGS.__dict__, 'web_password': 'secret'})

    @staticmethod
    def auth(password):
        return {'Authorization': 'Basic ' + base64.b64encode(f'any:{password}'.encode()).decode()}

    async def test_requires_password(self):
        response = await self.client.get('/api/status')
        self.assertEqual(response.status, 401)
        self.assertIn('Basic', response.headers['WWW-Authenticate'])

    async def test_wrong_password(self):
        response = await self.client.get('/', headers=self.auth('wrong'))
        self.assertEqual(response.status, 401)

    async def test_invalid_header(self):
        response = await self.client.get('/', headers={'Authorization': 'Basic !!!'})
        self.assertEqual(response.status, 401)

    async def test_correct_password(self):
        response = await self.client.get('/api/status', headers=self.auth('secret'))
        self.assertEqual(response.status, 200)

    async def put_flag(self, name, body, headers=None):
        headers = {**self.auth('secret'), 'X-Crafty-Bot': '1', **(headers or {})}
        return await self.client.put(f'/api/flags/{name}', json=body, headers=headers)

    async def test_set_flag(self):
        with self.assertLogs('core.web.dashboard', level='INFO'):
            response = await self.put_flag('command_stop', {'enabled': False})
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertTrue(data['editable'])
        self.assertFalse(next(flag for flag in data['flags'] if flag['name'] == 'command_stop')['enabled'])
        self.assertFalse(self.bot.flags.is_enabled('command_stop'))

    async def test_set_flag_updates_auto_stop_status(self):
        await (await self.client.get('/api/status', headers=self.auth('secret'))).json()
        with self.assertLogs('core.web.dashboard', level='INFO'):
            await self.put_flag('auto_stop', {'enabled': True})
        data = await (await self.client.get('/api/status', headers=self.auth('secret'))).json()
        self.assertEqual(data['bot']['auto_stop'], SETTINGS.auto_stop_interval)

    async def test_set_flag_without_csrf_header(self):
        with self.assertLogs('core.web.dashboard', level='WARNING'):
            response = await self.client.put('/api/flags/command_stop', json={'enabled': False},
                                             headers=self.auth('secret'))
        self.assertEqual(response.status, 400)
        self.assertTrue(self.bot.flags.is_enabled('command_stop'))

    async def test_set_flag_requires_password(self):
        response = await self.client.put('/api/flags/command_stop', json={'enabled': False},
                                         headers={'X-Crafty-Bot': '1'})
        self.assertEqual(response.status, 401)

    async def test_set_invalid_flag(self):
        for name, body in (('nope', {'enabled': True}), ('command_stop', {'enabled': 'no'})):
            with self.subTest(name=name, body=body), self.assertLogs('core.web.dashboard', level='WARNING'):
                response = await self.put_flag(name, body)
                self.assertEqual(response.status, 400)

    async def test_set_flag_body_not_an_object(self):
        response = await self.put_flag('command_stop', [])
        self.assertEqual(response.status, 400)

    async def put_level(self, level, headers=None):
        headers = {**self.auth('secret'), 'X-Crafty-Bot': '1', **(headers or {})}
        return await self.client.put('/api/log-level', json={'level': level}, headers=headers)

    async def test_set_log_level(self):
        with self.assertLogs('core.web.dashboard', level='WARNING') as logs:
            response = await self.put_level('debug')
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())['level'], 'DEBUG')
        self.assertEqual(logging.getLogger('core').level, logging.DEBUG)
        self.assertEqual(logging.getLogger().level, logging.INFO)  # libraries stay at INFO
        self.assertIn('from INFO to DEBUG', logs.output[0])

    async def test_set_invalid_log_level(self):
        response = await self.put_level('LOUD')
        self.assertEqual(response.status, 400)
        self.assertEqual(logging.getLogger('core').level, logging.INFO)

    async def test_set_log_level_without_csrf_header(self):
        with self.assertLogs('core.web.dashboard', level='WARNING'):
            response = await self.client.put('/api/log-level', json={'level': 'DEBUG'}, headers=self.auth('secret'))
        self.assertEqual(response.status, 400)
        self.assertEqual(logging.getLogger('core').level, logging.INFO)

    async def test_logs_require_password(self):
        response = await self.client.get('/api/logs')
        self.assertEqual(response.status, 401)

    async def test_set_flag_invalid_json(self):
        response = await self.client.put('/api/flags/command_stop', data='{', headers={
            **self.auth('secret'), 'X-Crafty-Bot': '1', 'Content-Type': 'application/json'})
        self.assertEqual(response.status, 400)

    async def test_set_flag_save_error(self):
        with patch.object(self.bot.flags, 'set', side_effect=FlagSaveError('disk full')), \
                self.assertLogs('core.web.dashboard', level='ERROR'):
            response = await self.put_flag('command_stop', {'enabled': False})
        self.assertEqual(response.status, 500)
        self.assertNotIn('disk full', (await response.json())['error'])

    async def test_health_without_password(self):
        response = await self.client.get('/healthz')
        self.assertEqual(response.status, 200)


class TestDashboardLifecycle(unittest.IsolatedAsyncioTestCase):

    async def test_start_and_stop(self):
        settings = Settings(**{**SETTINGS.__dict__, 'web_port': 18765})
        dashboard = WebDashboard(make_bot(settings))
        with self.assertLogs('core.web.dashboard', level='INFO') as logs:
            await dashboard.cog_load()
            await dashboard.cog_unload()
        self.assertIn('127.0.0.1:18765', logs.output[0])
        self.assertIn('no WEB_PASSWORD', logs.output[0])


class TestDashboardStartErrors(unittest.IsolatedAsyncioTestCase):

    async def test_port_in_use(self):
        with socket.socket() as blocker:
            blocker.bind(('127.0.0.1', 0))
            blocker.listen()
            port = blocker.getsockname()[1]
            dashboard = WebDashboard(make_bot(Settings(**{**SETTINGS.__dict__, 'web_port': port})))
            with self.assertRaises(DashboardStartError) as cm:
                await dashboard.cog_load()
        self.assertIn(f'port {port} is already in use', str(cm.exception))
        self.assertIsNone(dashboard._runner)  # pylint: disable=protected-access

    def test_messages(self):
        cases = [
            (OSError(errno.EACCES, 'denied'), 'above 1023'),
            (OSError(errno.EADDRNOTAVAIL, 'not available'), 'not an address of this machine'),
            (socket.gaierror(-2, 'Name or service not known'), 'not an address of this machine'),
            (OSError("could not bind on any address out of [('10.0.0.1', 80)]"), 'not an address of this machine'),
            (OSError(errno.EIO, 'io error'), 'io error'),
        ]
        for error, expected in cases:
            with self.subTest(error=error):
                self.assertIn(expected, describe_bind_error(error, 'nohost', 80))


if __name__ == '__main__':
    unittest.main()
