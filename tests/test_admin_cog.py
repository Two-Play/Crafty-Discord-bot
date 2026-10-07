import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

from core.cogs.admin import AdminCommands
from core.config import Settings


class TestAdminCommands(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.bot = MagicMock()
        self.bot.guild = discord.Object(id=123)
        self.bot.tree.sync = AsyncMock(return_value=[1, 2, 3])
        self.bot.crafty.login = AsyncMock()
        self.bot.settings = Settings(server_url='https://crafty.local', discord_token='d',
                                     crafty_username='user', crafty_password='pw')
        self.cog = AdminCommands(self.bot)
        self.ctx = MagicMock()
        self.ctx.reply = AsyncMock()

    async def invoke(self, command):
        await command.callback(self.cog, self.ctx)

    async def test_sync_to_guild(self):
        await self.invoke(self.cog.sync)
        self.bot.tree.copy_global_to.assert_called_once_with(guild=self.bot.guild)
        self.bot.tree.sync.assert_awaited_once_with(guild=self.bot.guild)
        self.ctx.reply.assert_awaited_once_with('3 commands synced')

    async def test_sync_globally(self):
        self.bot.guild = None
        await self.invoke(self.cog.sync)
        self.bot.tree.copy_global_to.assert_not_called()
        self.bot.tree.sync.assert_awaited_once_with(guild=None)

    async def test_clear(self):
        await self.invoke(self.cog.clear)
        self.bot.tree.clear_commands.assert_called_once_with(guild=self.bot.guild)

    async def test_list_commands(self):
        self.bot.tree.get_commands.return_value = [1, 2]
        await self.invoke(self.cog.list_commands)
        self.ctx.reply.assert_awaited_once_with('Got 2 commands')

    async def test_get_token(self):
        await self.invoke(self.cog.get_token)
        self.bot.crafty.login.assert_awaited_once_with('user', 'pw')
        self.ctx.reply.assert_awaited_once_with('Token successfully retrieved')

    async def test_get_token_without_credentials(self):
        self.bot.settings = Settings(server_url='https://crafty.local', discord_token='d', crafty_token='c')
        await self.invoke(self.cog.get_token)
        self.bot.crafty.login.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
