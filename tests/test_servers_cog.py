import unittest
from unittest.mock import AsyncMock, MagicMock

from discord.ext import commands

from core.cogs.servers import ServerCommands, ServerId, select_backup
from core.crafty import CraftyAPIError, ServerAction
from core.flags import FeatureDisabled, FeatureFlags, flag_definitions

SERVER_ID = 'ff231030-910c-4aaa-bd83-50e03aedab1c'


class TestServerId(unittest.IsolatedAsyncioTestCase):

    async def test_valid(self):
        self.assertEqual(await ServerId().convert(MagicMock(), SERVER_ID.upper()), SERVER_ID)

    async def test_invalid(self):
        with self.assertRaises(commands.BadArgument):
            await ServerId().convert(MagicMock(), 'abc')


class TestServerCommands(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.client = MagicMock()
        self.client.list_servers = AsyncMock(return_value=[
            {'server_id': 'a', 'server_name': 'Survival'},
            {'server_id': 'b', 'server_name': 'Creative'},
        ])
        self.client.get_stats = AsyncMock()
        self.client.run_action = AsyncMock()
        self.cog = ServerCommands(self.client)
        self.ctx = MagicMock()
        self.ctx.reply = AsyncMock()

    def set_stats(self, running, online=0, **extra):
        self.client.get_stats.return_value = {'running': running, 'online': online, 'world_name': 'World',
                                              'int_ping_results': str(running), **extra}

    async def invoke(self, command, *args, **kwargs):
        await command.callback(self.cog, self.ctx, *args, **kwargs)

    def reply_text(self):
        return self.ctx.reply.call_args.args[0]

    async def test_list(self):
        await self.invoke(self.cog.list_servers)
        self.assertIn('Survival', self.reply_text())

    async def test_list_empty(self):
        self.client.list_servers.return_value = []
        await self.invoke(self.cog.list_servers)
        self.assertIn('No servers found', self.reply_text())

    async def test_stats(self):
        self.set_stats(running=False)
        await self.invoke(self.cog.stats, SERVER_ID)
        self.assertIn('World: World', self.reply_text())

    async def test_start(self):
        self.set_stats(running=False)
        await self.invoke(self.cog.start, SERVER_ID)
        self.client.run_action.assert_awaited_once_with(SERVER_ID, ServerAction.START)
        self.assertEqual(self.reply_text(), 'Server started')

    async def test_start_already_running(self):
        self.set_stats(running=True)
        await self.invoke(self.cog.start, SERVER_ID)
        self.client.run_action.assert_not_awaited()
        self.assertEqual(self.reply_text(), 'Server already running')

    async def test_stop(self):
        self.set_stats(running=True)
        await self.invoke(self.cog.stop, SERVER_ID)
        self.client.run_action.assert_awaited_once_with(SERVER_ID, ServerAction.STOP)
        self.assertEqual(self.reply_text(), 'Server stopped')

    async def test_stop_already_stopped(self):
        self.set_stats(running=False)
        await self.invoke(self.cog.stop, SERVER_ID)
        self.client.run_action.assert_not_awaited()
        self.assertEqual(self.reply_text(), 'Server already stopped')

    async def test_stop_with_players_online(self):
        self.set_stats(running=True, online=2)
        await self.invoke(self.cog.stop, SERVER_ID)
        self.client.run_action.assert_not_awaited()
        self.assertEqual(self.reply_text(), 'cannot stop server: 2 Player(s) online')

    async def test_restart(self):
        self.set_stats(running=True)
        await self.invoke(self.cog.restart, SERVER_ID)
        self.client.run_action.assert_awaited_once_with(SERVER_ID, ServerAction.RESTART)
        self.assertEqual(self.reply_text(), 'Server restarted')

    async def test_restart_with_players_online(self):
        self.set_stats(running=True, online=1)
        await self.invoke(self.cog.restart, SERVER_ID)
        self.client.run_action.assert_not_awaited()
        self.assertEqual(self.reply_text(), 'cannot restart server: 1 Player(s) online')

    async def test_stop_with_unknown_player_count(self):
        self.set_stats(running=True, int_ping_results='False')
        with self.assertLogs('core.cogs.servers', level='WARNING'):
            await self.invoke(self.cog.stop, SERVER_ID)
        self.client.run_action.assert_awaited_once_with(SERVER_ID, ServerAction.STOP)

    async def test_start_while_starting(self):
        self.set_stats(running=False, waiting_start=True)
        await self.invoke(self.cog.start, SERVER_ID)
        self.client.run_action.assert_not_awaited()
        self.assertEqual(self.reply_text(), 'Server is already starting')

    async def test_api_error_propagates(self):
        self.client.get_stats.side_effect = CraftyAPIError('down')
        with self.assertRaises(CraftyAPIError):
            await self.invoke(self.cog.start, SERVER_ID)

    async def test_autocomplete_filters_by_name(self):
        choices = await self.cog.server_autocomplete(MagicMock(), 'sur')
        self.assertEqual([(c.name, c.value) for c in choices], [('Survival', 'a')])

    async def test_autocomplete_uses_cache(self):
        await self.cog.server_autocomplete(MagicMock(), '')
        await self.cog.server_autocomplete(MagicMock(), '')
        self.client.list_servers.assert_awaited_once()

    async def test_autocomplete_api_error(self):
        self.client.list_servers.side_effect = CraftyAPIError('down')
        with self.assertLogs('core.cogs.servers', level='WARNING'):
            self.assertEqual(await self.cog.server_autocomplete(MagicMock(), ''), [])

    def set_backups(self, *backups):
        self.client.list_backups = AsyncMock(return_value=list(backups))
        self.client.run_backup = AsyncMock()

    async def test_backup_default(self):
        self.set_backups({'backup_id': 'b1', 'backup_name': 'Weekly'},
                         {'backup_id': 'b2', 'backup_name': 'Default', 'default': True})
        with self.assertLogs('core.cogs.servers', level='INFO'):
            await self.invoke(self.cog.backup, SERVER_ID)
        self.client.run_backup.assert_awaited_once_with(SERVER_ID, 'b2')
        self.assertIn('`Default` started', self.reply_text())

    async def test_backup_by_name(self):
        self.set_backups({'backup_id': 'b1', 'backup_name': 'Weekly'},
                         {'backup_id': 'b2', 'backup_name': 'Default', 'default': True})
        with self.assertLogs('core.cogs.servers', level='INFO'):
            await self.invoke(self.cog.backup, SERVER_ID, backup='weekly')
        self.client.run_backup.assert_awaited_once_with(SERVER_ID, 'b1')

    async def test_backup_unknown_name(self):
        self.set_backups({'backup_id': 'b1', 'backup_name': 'Weekly'})
        await self.invoke(self.cog.backup, SERVER_ID, backup='daily')
        self.client.run_backup.assert_not_awaited()
        self.assertIn('`Weekly`', self.reply_text())

    async def test_backup_none_configured(self):
        self.set_backups()
        await self.invoke(self.cog.backup, SERVER_ID)
        self.client.run_backup.assert_not_awaited()
        self.assertIn('No backup configured', self.reply_text())

    async def test_backup_is_owner_only(self):
        self.assertTrue(self.cog.backup.checks)

    async def test_backup_autocomplete(self):
        self.set_backups({'backup_id': 'b1', 'backup_name': 'Weekly'}, {'backup_id': 'b2', 'backup_name': 'Daily'})
        interaction = MagicMock()
        interaction.namespace.server_id = SERVER_ID
        choices = await self.cog.backup_autocomplete(interaction, 'we')
        self.assertEqual([c.value for c in choices], ['Weekly'])

    async def test_backup_autocomplete_without_server(self):
        self.set_backups({'backup_id': 'b1'})
        interaction = MagicMock()
        interaction.namespace.server_id = None
        self.assertEqual(await self.cog.backup_autocomplete(interaction, ''), [])
        self.client.list_backups.assert_not_awaited()


class TestSelectBackup(unittest.TestCase):

    def test_single_backup_is_used_without_default(self):
        self.assertEqual(select_backup([{'backup_id': 'b1'}], None), {'backup_id': 'b1'})

    def test_no_default_among_several(self):
        self.assertIsNone(select_backup([{'backup_id': 'b1'}, {'backup_id': 'b2'}], None))

    def test_by_id(self):
        self.assertEqual(select_backup([{'backup_id': 'b1'}, {'backup_id': 'b2'}], 'B2'), {'backup_id': 'b2'})


class TestServerCommandFlags(unittest.TestCase):

    def test_disabled_command_fails_the_check(self):
        flags = FeatureFlags(flag_definitions(), None)
        cog = ServerCommands(MagicMock(), flags)
        ctx = MagicMock()
        ctx.command.name = 'stop'
        self.assertTrue(cog.cog_check(ctx))
        flags.set('command_stop', False)
        with self.assertRaises(FeatureDisabled):
            cog.cog_check(ctx)

    def test_without_flags_everything_is_allowed(self):
        ctx = MagicMock()
        ctx.command.name = 'stop'
        self.assertTrue(ServerCommands(MagicMock()).cog_check(ctx))


if __name__ == '__main__':
    unittest.main()
