import unittest

from core.printing import print_server_info, print_server_status


class TestPrintServerInfo(unittest.TestCase):

    def test_server_info_correct_format(self):
        data = {
            'data': [
                {'server_id': 1, 'server_name': 'Server1', 'server_ip': '192.168.1.1', 'server_port': 25565},
                {'server_id': 2, 'server_name': 'Server2', 'server_ip': '192.168.1.2', 'server_port': 25566}
            ]
        }
        expected_output = (
            "```\nID: 1\nServer: Server1\n  IP: 192.168.1.1\n  Port: 25565\n```\n"
            "```\nID: 2\nServer: Server2\n  IP: 192.168.1.2\n  Port: 25566\n```\n"
        )
        self.assertEqual(print_server_info(data), expected_output)

    def test_server_info_empty_data(self):
        data = {'data': []}
        expected_output = ""
        self.assertEqual(print_server_info(data), expected_output)

    def test_server_info_missing_fields(self):
        data = {
            'data': [
                {'server_id': 1, 'server_name': 'Server1', 'server_ip': '192.168.1.1'},
                {'server_id': 2, 'server_name': 'Server2', 'server_port': 25566}
            ]
        }
        expected_output = (
            "```\nID: 1\nServer: Server1\n  IP: 192.168.1.1\n  Port: unknown\n```\n"
            "```\nID: 2\nServer: Server2\n  IP: unknown\n  Port: 25566\n```\n"
        )
        self.assertEqual(print_server_info(data), expected_output)


class TestPrintServerStatus(unittest.TestCase):

    def test_server_status_running(self):
        data = {
            'data': {
                'world_name': 'World1',
                'running': True,
                'players': 5,
                'version': '1.16.5',
                'cpu': 50,
                'mem': 1024,
                'mem_percent': 25
            }
        }
        expected_output = (
            "```\nWorld: World1\nRunning: True\nPlayers: 5\nVersion: 1.16.5\nCPU: 50%\nRAM: 1024MB (25%)\n```\n"
        )
        self.assertEqual(print_server_status(data), expected_output)

    def test_server_status_stopped(self):
        data = {
            'data': {
                'world_name': 'World1',
                'running': False,
                'cpu': '',
                'mem': '',
                'mem_percent': ''
            }
        }
        expected_output = "```\nWorld: World1\nRunning: False\n```\n"
        self.assertEqual(print_server_status(data), expected_output)

    def test_server_status_missing_fields(self):
        data = {
            'data': {
                'world_name': 'World1',
                'running': True,
                'players': 5,
                'version': '1.16.5',
                'cpu': 50,
                'mem': 23,
                'mem_percent': 12
            }
        }
        expected_output = (
            "```\nWorld: World1\nRunning: True\nPlayers: 5\nVersion: 1.16.5\nCPU: 50%\nRAM: 23MB (12%)\n```\n"
        )
        self.assertEqual(print_server_status(data), expected_output)


if __name__ == '__main__':
    unittest.main()