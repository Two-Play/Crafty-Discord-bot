import os
import unittest
from unittest.mock import patch, MagicMock

import requests

from core.network import is_response_successful, get_response, get_json_response


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
    def test_get_response_successful(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        response = get_response('/test')
        self.assertEqual(response.status_code, 200)

    @patch('core.network.requests.get')
    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'CRAFTY_TOKEN': 'dummy_token'})
    def test_get_response_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout
        with self.assertRaises(requests.Timeout):
            get_response('/test', timeout=1)

    @patch('core.network.get_response')
    @patch.dict(os.environ, {'SERVER_URL': 'http://example.com', 'CRAFTY_TOKEN': 'dummy_token'})
    def test_get_json_response_successful(self, mock_get_response):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'key': 'value'}
        mock_get_response.return_value = mock_response
        self.assertEqual(get_json_response('/test'), {'key': 'value'})

    @patch('core.network.get_response')
    def test_get_json_response_failure(self, mock_get_response):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get_response.return_value = mock_response
        self.assertEqual(get_json_response('/test'), {})
