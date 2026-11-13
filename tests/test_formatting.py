import unittest

from core.formatting import format_memory, format_players, format_server_list, format_server_stats, split_message


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
        self.assertEqual(''.join(format_server_list(data['data'])), expected_output)

    def test_server_info_empty_data(self):
        data = {'data': []}
        expected_output = ""
        self.assertEqual(''.join(format_server_list(data['data'])), expected_output)

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
        self.assertEqual(''.join(format_server_list(data['data'])), expected_output)


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


class TestSplitMessage(unittest.TestCase):

    def test_fits_in_one_message(self):
        self.assertEqual(split_message(['a', 'b']), ['ab'])

    def test_splits_between_parts(self):
        self.assertEqual(split_message(['aaa', 'bbb', 'c'], limit=5), ['aaa', 'bbbc'])

    def test_long_part_is_cut(self):
        self.assertEqual(split_message(['abcdefg'], limit=3), ['abc'])

    def test_many_servers_stay_below_discord_limit(self):
        servers = [{'server_id': f'{n:036d}', 'server_name': f'Server {n}', 'server_ip': '10.0.0.1',
                    'server_port': 25565} for n in range(60)]
        messages = split_message(['Server information:\n', *format_server_list(servers)])
        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= 2000 for message in messages))
        self.assertTrue(all(message.count('```') % 2 == 0 for message in messages[1:]))


class TestFormatPlayers(unittest.TestCase):

    def test_long_player_list_is_shortened(self):
        names = [f'player{n}' for n in range(30)]
        text = format_players({'int_ping_results': 'True', 'online': 30, 'max': 50, 'players': repr(names)})
        self.assertIn('player19, and 10 more', text)
        self.assertNotIn('player20', text)


if __name__ == '__main__':
    unittest.main()
