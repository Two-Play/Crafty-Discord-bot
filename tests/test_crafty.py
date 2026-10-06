import unittest
from unittest.mock import MagicMock

import requests

from core.crafty import CraftyAPIError, CraftyClient, ServerAction, parse_server_id

SERVER_ID = 'ff231030-910c-4aaa-bd83-50e03aedab1c'


def make_response(status_code=200, body=None):
    response = MagicMock()
    response.status_code = status_code
    response.ok = status_code < 400
    response.json.return_value = {'status': 'ok', 'data': {}} if body is None else body
    return response


class TestParseServerId(unittest.TestCase):

    def test_valid(self):
        self.assertEqual(parse_server_id(SERVER_ID), SERVER_ID)

    def test_normalizes(self):
        self.assertEqual(parse_server_id(SERVER_ID.upper().replace('-', '')), SERVER_ID)

    def test_invalid(self):
        for value in ('abc', '', None, '../stats'):
            with self.subTest(value=value):
                self.assertIsNone(parse_server_id(value))


class TestCraftyClient(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.session = MagicMock()
        self.session.headers = {}
        self.client = CraftyClient('https://crafty.local/', 'token', session=self.session, timeout=3)

    def test_sets_auth_header(self):
        self.assertEqual(self.session.headers['Authorization'], 'Bearer token')

    async def test_list_servers(self):
        self.session.request.return_value = make_response(body={'status': 'ok', 'data': [{'server_id': 'a'}]})
        self.assertEqual(await self.client.list_servers(), [{'server_id': 'a'}])
        self.session.request.assert_called_once_with('GET', 'https://crafty.local/api/v2/servers', json=None,
                                                     timeout=3, verify=False)

    async def test_get_stats(self):
        self.session.request.return_value = make_response(body={'status': 'ok', 'data': {'running': True}})
        self.assertEqual(await self.client.get_stats(SERVER_ID), {'running': True})
        self.assertEqual(self.session.request.call_args.args[1],
                         f'https://crafty.local/api/v2/servers/{SERVER_ID}/stats')

    async def test_run_action(self):
        self.session.request.return_value = make_response()
        await self.client.run_action(SERVER_ID, ServerAction.RESTART)
        self.assertEqual(self.session.request.call_args.args,
                         ('POST', f'https://crafty.local/api/v2/servers/{SERVER_ID}/action/restart_server'))

    async def test_login_sets_token(self):
        self.session.request.return_value = make_response(body={'status': 'ok', 'data': {'token': 'new'}})
        await self.client.login('user', 'pw')
        self.assertEqual(self.session.request.call_args.kwargs['json'], {'username': 'user', 'password': 'pw'})
        self.assertEqual(self.session.headers['Authorization'], 'Bearer new')

    async def test_login_without_token_raises(self):
        self.session.request.return_value = make_response(body={'status': 'ok', 'data': {}})
        with self.assertRaises(CraftyAPIError):
            await self.client.login('user', 'pw')

    async def test_network_error_raises(self):
        self.session.request.side_effect = requests.ConnectionError('down')
        with self.assertRaises(CraftyAPIError):
            await self.client.list_servers()

    async def test_http_error_raises(self):
        self.session.request.return_value = make_response(status_code=403)
        with self.assertRaises(CraftyAPIError):
            await self.client.list_servers()

    async def test_invalid_json_raises(self):
        response = make_response()
        response.json.side_effect = ValueError
        self.session.request.return_value = response
        with self.assertRaises(CraftyAPIError):
            await self.client.list_servers()

    async def test_error_status_raises(self):
        self.session.request.return_value = make_response(body={'status': 'error', 'error': 'NOT_AUTHORIZED'})
        with self.assertRaises(CraftyAPIError):
            await self.client.run_action(SERVER_ID, ServerAction.START)


if __name__ == '__main__':
    unittest.main()
