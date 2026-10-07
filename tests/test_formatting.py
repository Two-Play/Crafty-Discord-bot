import unittest

from core.formatting import format_memory, format_server_list, format_server_stats


class TestFormatServerList(unittest.TestCase):

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
        self.assertEqual(format_server_list(data['data']), expected_output)

    def test_server_info_empty_data(self):
        data = {'data': []}
        expected_output = ""
        self.assertEqual(format_server_list(data['data']), expected_output)

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
        self.assertEqual(format_server_list(data['data']), expected_output)


class TestFormatServerStats(unittest.TestCase):

    # Shape of GET /api/v2/servers/{id}/stats in Crafty 4.11
    RUNNING = {
        'world_name': 'World1', 'running': True, 'int_ping_results': 'True', 'online': 2, 'max': 20,
        'players': "['Steve', 'Alex']", 'version': '1.21.4', 'cpu': 12.5, 'mem': 1610612736.0,
        'mem_percent': 25.0, 'waiting_start': False, 'updating': False, 'importing': False, 'crashed': False,
    }

    def test_server_status_running(self):
        expected_output = (
            "```\nWorld: World1\nRunning: True\nPlayers: 2/20 (Steve, Alex)\nVersion: 1.21.4\n"
            "CPU: 12.5%\nRAM: 1.5 GB (25.0%)\n```\n"
        )
        self.assertEqual(format_server_stats(self.RUNNING), expected_output)

    def test_server_status_stopped(self):
        data = {'world_name': 'World1', 'running': False, 'int_ping_results': 'False', 'online': 0,
                'players': 'False', 'version': 'False', 'cpu': 0.0, 'mem': 0.0, 'mem_percent': 0.0}
        self.assertEqual(format_server_stats(data), "```\nWorld: World1\nRunning: False\n```\n")

    def test_server_status_ping_failed(self):
        data = {**self.RUNNING, 'int_ping_results': 'False', 'online': 0, 'max': 0, 'players': 'False',
                'version': 'False', 'waiting_start': True}
        output = format_server_stats(data)
        self.assertIn('Status: starting', output)
        self.assertIn('Players: unknown', output)
        self.assertIn('Version: unknown', output)

    def test_server_status_missing_fields(self):
        output = format_server_stats({'running': True})
        self.assertIn('World: unknown', output)
        self.assertIn('Players: unknown', output)
        self.assertIn('RAM: ? (?%)', output)


class TestFormatMemory(unittest.TestCase):

    def test_units(self):
        self.assertEqual(format_memory(512), '512 B')
        self.assertEqual(format_memory(2048), '2.0 KB')
        self.assertEqual(format_memory(1610612736.0), '1.5 GB')

    def test_already_formatted(self):
        self.assertEqual(format_memory('1.5GB'), '1.5GB')
        self.assertEqual(format_memory(None), '?')


if __name__ == '__main__':
    unittest.main()
