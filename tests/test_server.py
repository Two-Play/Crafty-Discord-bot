import unittest
from unittest.mock import patch, MagicMock

from core.server import stop_server, get_player_count, is_server_running


class TestServerFunctions(unittest.TestCase):

    @patch('core.server.get_json_response')
    def test_stop_server_successful(self, mock_get_json_response):
        mock_get_json_response.return_value = {'status': 'ok'}
        self.assertTrue(stop_server(1))

    @patch('core.server.get_json_response')
    def test_stop_server_failure(self, mock_get_json_response):
        mock_get_json_response.return_value = {'status': 'error'}
        self.assertFalse(stop_server(1))

    @patch('core.server.get_json_response')
    def test_get_player_count_successful(self, mock_get_json_response):
        mock_get_json_response.return_value = {'data': {'online': 5}}
        self.assertEqual(get_player_count(1), 5)

    @patch('core.server.get_json_response')
    def test_get_player_count_failure(self, mock_get_json_response):
        mock_get_json_response.return_value = {}
        self.assertEqual(get_player_count(1), -1)

    @patch('core.server.get_json_response')
    def test_is_server_running_successful(self, mock_get_json_response):
        mock_get_json_response.return_value = {'data': {'running': True}}
        self.assertTrue(is_server_running(1))

    @patch('core.server.get_json_response')
    def test_is_server_running_failure(self, mock_get_json_response):
        mock_get_json_response.return_value = {}
        self.assertFalse(is_server_running(1))

if __name__ == '__main__':
    unittest.main()