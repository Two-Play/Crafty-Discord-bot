"""
This is the main file of the bot. It contains the
main loop and the event handlers.
"""

import asyncio
import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import is_owner
from dotenv import load_dotenv

from core.constants import AUTO_STOP_SLEEP, GUILD_ID, API_ENDPOINT
from core.helper import check_env_vars
from core.network import get_json_response
from core.printing import print_server_info, print_server_status
from core.server import is_server_running, stop_server, get_player_count

# Load environment variables from .env file
load_dotenv()
check_env_vars()

SERVER_URL = os.environ['SERVER_URL']
if 'USERNAME' in os.environ and 'PASSWORD' in os.environ:
    USERNAME = os.environ['USERNAME']
    PASSWORD = os.environ['PASSWORD']

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)


# stop server after 1 hour of inactivity (no players online)
async def auto_stop():
    """
    Automatically stop servers that have been inactive for a certain period of time.
    """
    while True:
        # get list of servers ids and loop through them and add only the ones that are running
        data = get_json_response('/api/v2/servers',
                                 'failed to get server list')
        if not data:
            print('failed to get server list')
            return
        server_ids = [server['server_id'] for server in data['data']]

        for server_id in server_ids:
            if is_server_running(server_id) and get_player_count(server_id) == 0:
                stop_server(server_id)

        await asyncio.sleep(AUTO_STOP_SLEEP)  # task runs every hour


@bot.event
async def on_ready():
    print('Bot is ready. {}'.format(bot.user))
    print("Crafty Bot version 0.1")

    await auto_stop()
    # get_token()


# @bot.tree.command(name="rps")/*
# @app_commands.guilds(discord.Object(id=GUILD_ID))@app_commands.choices(choices=[
#     app_commands.Choice(name="Rock", value="rock"),
#     app_commands.Choice(name="Paper", value="paper"),
#     app_commands.Choice(name="Scissors", value="scissors"),
#     ])
# async def rps(i: discord.Interaction, choices: app_commands.Choice[str]):
#     if (choices.value == 'rock'):
#         counter = 'paper'
#     elif (choices.value == 'paper'):
#         counter = 'scissors'
#     else:
#         counter = 'rock'


@bot.hybrid_command(name='sync', description='Sync commands')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@is_owner()
async def sync(ctx) -> None:
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    # add commands to the app commands
    await ctx.reply("{} commands synced".format(len(synced)))


@bot.hybrid_command(name='get_token', description='get token if not set (not recommended)')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@is_owner()
async def get_token(ctx):
    print('get_token')

    data = get_json_response('/api/v2/auth/login', 'failed to get token')
    if not data:
        await ctx.reply('failed to get token')
        return

    os.environ['CRAFTY_TOKEN'] = data['data']['token']
    await ctx.send('Toke successful retrieved')


@bot.hybrid_command(name='list', description='get server list')
@app_commands.guilds(discord.Object(id=GUILD_ID))  # get the list of servers
async def get_list(ctx):
    print('servers')
    data = get_json_response('/api/v2/servers', 'failed to get server list')
    server_info_text = print_server_info(data)

    await ctx.reply(f"Serverinformationen:\n{server_info_text}")


# get statistics of a server
@bot.hybrid_command(name='stats', description='get server stats')
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def stats(ctx, server_id):
    print('stats')
    if not server_id:
        await ctx.reply('Please provide a server id')
        return

    data = get_json_response(API_ENDPOINT + str(server_id) + '/stats', 'failed to get server stats')
    if not data:
        await ctx.reply('failed to get server stats')
        return

    server_info_text = print_server_status(data)
    await ctx.reply(f"Serverinformationen:\n{server_info_text}")


# start a server
@bot.hybrid_command(name='start', description='start a server')
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def start(ctx, server_id):
    print('start')

    # check if server is already running
    if is_server_running(server_id, ctx):
        await ctx.reply('Server already running')
        return

    data = get_json_response(API_ENDPOINT + str(server_id) + '/action/start_server',
                             'failed to start server')
    if not data:
        await ctx.reply('failed to start server')
        return

    if data['status'] == "ok":
        await ctx.reply('Server started')


# stop a server
@bot.hybrid_command(name='stop', description='stop a server')
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def stop(ctx, server_id):
    print('stop')

    # check if server is already stopped
    if not is_server_running(server_id, ctx):
        await ctx.reply('Server already stopped')
        return

    # check if player is online
    player_count = get_player_count(server_id, ctx)
    if player_count != 0:
        await ctx.reply(f'cannot stop server: {player_count} Player(s) online')
        return

    if stop_server(server_id):
        await ctx.reply('Server stopped')
    else:
        await ctx.reply('failed to stop server')


# show help
# @bot.command()
# @bot.tree.command(name='bot_help', description='Show help')
@bot.hybrid_command(name='bot_help', description='Show help')
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def bot_help(interaction: discord.Interaction):
    print('help')

    help_text = """
    ```
    >list
    >stats <server_id>
    >start <server_id>
    >stop <server_id>
    ```
    """
    # await ctx.send(help_text)
    await interaction.response.send_message(help_text)


# command not found
@bot.event
async def on_command_error(ctx, error):
    """
    Handle command not found errors
    """
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found. Use `>bot_help` to get a list of available commands.')


bot.run(os.environ['DISCORD_TOKEN'])
