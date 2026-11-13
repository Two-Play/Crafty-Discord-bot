import unittest
from unittest.mock import AsyncMock, MagicMock

from core.cogs.auto_stop import AutoStop
from core.crafty import CraftyAPIError, ServerAction
from core.flags import FeatureFlags, flag_definitions


class TestAutoStop(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.client = MagicMock()
        self.client.list_servers = AsyncMock(return_value=[{'server_id': 'idle'}, {'server_id': 'busy'},
                                                           {'server_id': 'off'}])
        self.client.get_stats = AsyncMock(side_effect=lambda server_id: {
            'idle': {'running': True, 'online': 0, 'int_ping_results': 'True'},
            'idle2': {'running': True, 'online': 0, 'int_ping_results': 'True'},
            'busy': {'running': True, 'online': 3, 'int_ping_results': 'True'},
            'off': {'running': False, 'online': 0, 'int_ping_results': 'False'},
            'unpingable': {'running': True, 'online': 0, 'int_ping_results': 'False'},
            'starting': {'running': True, 'online': 0, 'int_ping_results': 'True', 'waiting_start': True},
        }[server_id])
        self.client.run_action = AsyncMock()
        self.cog = AutoStop(self.client, interval=60)

    async def test_interval(self):
        self.assertEqual(self.cog.stop_idle_servers.seconds, 60)

    async def check(self, cog=None, times=2):
        """Run the auto stop check; servers are only stopped when they were empty at two checks in a row."""
        cog = cog or self.cog
        for _ in range(times):
            await cog.stop_idle_servers.coro(cog)

    async def test_stops_only_idle_running_servers(self):
        self.client.list_servers.return_value = [{'server_id': 'idle'}, {'server_id': 'busy'}, {'server_id': 'off'}]
        with self.assertLogs('core.cogs.auto_stop', level='INFO'):
            await self.check()
        self.client.run_action.assert_awaited_once_with('idle', ServerAction.STOP)

    async def test_first_empty_check_does_not_stop(self):
        with self.assertLogs('core.cogs.auto_stop', level='INFO') as logs:
            await self.check(times=1)
        self.client.run_action.assert_not_awaited()
        self.assertIn('stopping it at the next check', logs.output[0])

    async def test_players_joining_between_checks_reset_the_idle_state(self):
        self.client.list_servers.return_value = [{'server_id': 'idle'}]
        stats = {'running': True, 'online': 0, 'int_ping_results': 'True'}
        self.client.get_stats.side_effect = lambda server_id: stats
        with self.assertLogs('core.cogs.auto_stop', level='INFO'):
            await self.check(times=1)
            stats = {**stats, 'online': 2}
            await self.check(times=1)
            stats = {**stats, 'online': 0}
            await self.check(times=1)
        self.client.run_action.assert_not_awaited()

    async def test_skips_servers_with_unknown_player_count_or_busy(self):
        self.client.list_servers.return_value = [{'server_id': 'unpingable'}, {'server_id': 'starting'}]
        with self.assertLogs('core.cogs.auto_stop', level='INFO'):
            await self.check()
        self.client.run_action.assert_not_awaited()

    async def test_skips_servers_without_id(self):
        self.client.list_servers.return_value = [{'server_name': 'broken'}]
        await self.check()
        self.client.get_stats.assert_not_awaited()

    async def test_disabled_by_flag(self):
        cog = AutoStop(self.client, interval=60, flags=FeatureFlags(flag_definitions(False), None))
        self.assertFalse(cog.enabled)
        await self.check(cog)
        self.client.list_servers.assert_not_awaited()

    async def test_enabled_by_flag(self):
        flags = FeatureFlags(flag_definitions(False), None)
        flags.set('auto_stop', True)
        cog = AutoStop(self.client, interval=60, flags=flags)
        self.client.list_servers.return_value = [{'server_id': 'idle'}]
        with self.assertLogs('core.cogs.auto_stop', level='INFO'):
            await self.check(cog)
        self.client.run_action.assert_awaited_once_with('idle', ServerAction.STOP)

    async def test_list_error_is_handled(self):
        self.client.list_servers.side_effect = CraftyAPIError('down')
        with self.assertLogs('core.cogs.auto_stop', level='WARNING'):
            await self.check()
        self.client.run_action.assert_not_awaited()

    async def test_unexpected_list_error_keeps_the_loop_alive(self):
        self.client.list_servers.side_effect = KeyError('data')
        with self.assertLogs('core.cogs.auto_stop', level='ERROR'):
            await self.check(times=1)

    async def test_error_on_one_server_continues_with_others(self):
        self.client.run_action.side_effect = CraftyAPIError('down')
        self.client.list_servers.return_value = [{'server_id': 'idle'}, {'server_id': 'idle2'}]
        with self.assertLogs('core.cogs.auto_stop', level='WARNING'):
            await self.check()
        self.assertEqual(self.client.run_action.await_count, 2)

    async def test_unexpected_error_on_one_server_continues_with_others(self):
        self.client.list_servers.return_value = [{'server_id': 'broken'}, {'server_id': 'idle'}]
        with self.assertLogs('core.cogs.auto_stop', level='ERROR'):
            await self.check()
        self.client.run_action.assert_awaited_once_with('idle', ServerAction.STOP)


if __name__ == '__main__':
    unittest.main()
