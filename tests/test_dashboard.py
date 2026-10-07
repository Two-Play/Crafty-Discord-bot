import base64
import math
import unittest
from unittest.mock import AsyncMock, MagicMock

from aiohttp.test_utils import TestClient, TestServer

from core.config import Settings
from core.crafty import CraftyAPIError
from core.web.dashboard import WebDashboard, summarize_server

SETTINGS = Settings(server_url='https://crafty.local', discord_token='discord', crafty_token='crafty',
                    web_enabled=True)

RUNNING_STATS = {'running': True, 'int_ping_results': 'True', 'online': 1, 'max': 10, 'players': "['Steve']",
                 'version': '1.21.4', 'cpu': 3.5, 'mem': 1073741824.0, 'mem_percent': 12.0}


def make_bot(settings=SETTINGS):
    bot = MagicMock()
    bot.settings = settings
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


if __name__ == '__main__':
    unittest.main()
