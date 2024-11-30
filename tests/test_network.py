import os
import unittest
from unittest.mock import patch, MagicMock

import requests

from core.network import is_response_successful, get_json_response, send_request


class TestNetwork(unittest.TestCase):

    @patch('core.network.requests.get')
    def test_is_response_successful_status_200(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        self.assertTrue(is_response_successful(mock_response))

    @patch('core.network.requests.get')
    def test_is_response_successful_status_not_200(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        self.assertFalse(is_response_successful(mock_response))

    @patch('core.network.requests.get')
    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'CRAFTY_TOKEN': 'dummy_token'})
    def test_send_request_successful(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        response = send_request('/')
        self.assertEqual(response.status_code, 200)

    # @patch('core.network.requests.get')
    # @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'CRAFTY_TOKEN': 'dummy_token'})
    # def test_send_request_timeout(self, mock_get):
    #     mock_get.side_effect = requests.Timeout
    #     with self.assertRaises(requests.Timeout):
    #         send_request('/test', timeout=1)

    @patch('core.network.send_request')
    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'CRAFTY_TOKEN': 'dummy_token'})
    def test_get_json_response_successful(self, mock_send_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'key': 'value'}
        mock_send_request.return_value = mock_response
        self.assertEqual(get_json_response('/test'), {'key': 'value'})

    @patch('core.network.send_request')
    def test_get_json_response_failure(self, mock_send_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_send_request.return_value = mock_response
        self.assertEqual(get_json_response('/test'), {})
