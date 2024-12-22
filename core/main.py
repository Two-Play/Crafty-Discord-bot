"""
This is the main file of the bot. It contains the
main loop and the event handlers.
"""

import asyncio
import os
import sys
import logging

import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import is_owner
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logger = logging.getLogger('CraftyDiscordBot')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - [CraftyBot] - [%(levelname)s] -> %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Load environment variables from .env file
logger.debug('Loading environment variables')
load_dotenv()
logger.debug('Environment variables loaded')
from core.helper import check_env_vars, check_server_id, get_server_list

check_env_vars()

from core.network import get_json_response, HttpMethod
from core.printing import print_server_info, print_server_status
from core.server import is_server_running, stop_server, get_player_count
from core.custom_help_command import CustomHelpCommand
from core.constants import AUTO_STOP_SLEEP_TIME, GUILD_ID, API_ENDPOINT, CRAFTY_BOT_VERSION

SERVER_URL = os.environ['SERVER_URL']
if 'USERNAME' in os.environ and 'PASSWORD' in os.environ:
    USERNAME = os.environ['USERNAME']
    PASSWORD = os.environ['PASSWORD']

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents, help_command=CustomHelpCommand())


# stop server after 1 hour of inactivity (no players online)
async def auto_stop():
    """
    Automatically stop servers that have been inactive for a certain period of time.
    """
    logger.debug('auto stop function called')
    while True:
        # get list of servers ids and loop through them and add only the ones that are running
        data = get_json_response(API_ENDPOINT,
                                 'failed to get server list')
        if not data:
            logger.debug('failed to get server list (data is None)')
            return
        server_ids = [server['server_id'] for server in data['data']]

        for server_id in server_ids:
            if is_server_running(server_id) and get_player_count(server_id) == 0:
                stop_server(server_id)

        await asyncio.sleep(AUTO_STOP_SLEEP_TIME)  # task runs every hour


@bot.event
async def on_ready():
    logger.info('Bot is ready. {}'.format(bot.user))
    logger.info("Crafty Bot version {}".format(CRAFTY_BOT_VERSION))
    logger.debug("Server URL: {}".format(SERVER_URL))
    logger.debug("GUILD ID: {}".format(GUILD_ID))

    try:
        if 'ENABLE_AUTO_STOP_SERVER' in os.environ and os.environ['ENABLE_AUTO_STOP_SERVER'] == 'true':
            logger.debug('auto stop enabled')
            # bot.loop.create_task(auto_stop())
            await auto_stop()
        else:
            logger.debug('auto stop disabled')
    except Exception as e:
        logger.debug(e)
    # get_token()


@bot.hybrid_command(name='sync', description='Sync slash commands')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@is_owner()
async def sync(ctx) -> None:
    logger.debug('sync')
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    # add commands to the app commands
    await ctx.reply("{} commands synced".format(len(synced)))


@bot.hybrid_command(name='clear', description='Clear all slash commands')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@is_owner()
async def clear(ctx) -> None:
    logger.debug('clear')
    bot.tree.clear_commands(guild=discord.Object(id=GUILD_ID))
    await ctx.reply("All commands cleared")


@bot.hybrid_command(name='commands', description='Get all slash commands')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@is_owner()
async def get_commands(ctx) -> None:
    logger.debug('commands')
    get_all_commands = bot.tree.get_commands(guild=discord.Object(id=GUILD_ID))
    await ctx.reply(f"Got {len(get_all_commands)} commands")


@bot.hybrid_command(name='get_token', description='get token if not set (not recommended)')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@is_owner()
async def get_token(ctx):
    logger.debug('get_token')

    data = get_json_response('/api/v2/auth/login', 'failed to get token')
    if not data:
        await ctx.reply('failed to get token')
        logger.debug('failed to get token')
        return

    os.environ['CRAFTY_TOKEN'] = data['data']['token']
    await ctx.send('Toke successful retrieved')
    logger.debug('Token successful retrieved')


@bot.hybrid_command(name='list', description='get server list')
@app_commands.guilds(discord.Object(id=GUILD_ID))  # get the list of servers
async def get_list(ctx):
    logger.debug('servers')
    data = get_json_response('/api/v2/servers', 'failed to get server list')
    if not data:
        await ctx.reply('failed to get server list')
        logger.debug('failed to get server list (data is None)')
        return
    server_info_text = print_server_info(data)

    await ctx.reply(f"Server information:\n{server_info_text}")


# get statistics of a server
@bot.hybrid_command(name='stats', description='get server stats')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.autocomplete(server_id=get_server_list)
async def stats(ctx, server_id):
    logger.debug('stats')

    if not await check_server_id(server_id, ctx):
        return

    data = get_json_response(API_ENDPOINT + str(server_id) + '/stats', 'failed to get server stats')
    if not data:
        await ctx.reply('failed to get server stats')
        logger.debug('failed to get server stats (data is None)')
        return

    server_info_text = print_server_status(data)
    await ctx.reply(f"Server information:\n{server_info_text}")


# start a server
@bot.hybrid_command(name='start', description='start a server')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.autocomplete(server_id=get_server_list)
async def start(ctx, server_id):
    logger.debug('start')

    if not await check_server_id(server_id, ctx):
        return

    # check if server is already running
    if is_server_running(server_id, ctx):
        await ctx.reply('Server already running')
        return

    data = get_json_response(API_ENDPOINT + str(server_id) + '/action/start_server',
                             'failed to start server', method=HttpMethod.POST)
    if not data:
        await ctx.reply('failed to start server')
        logger.debug('failed to start server (data is None)')
        return

    if data['status'] == "ok":
        await ctx.reply('Server started')
        logger.debug('Server started {}'.format(server_id))


# stop a server
@bot.hybrid_command(name='stop', description='stop a server')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.autocomplete(server_id=get_server_list)
async def stop(ctx, server_id):
    logger.debug('stop')

    if not await check_server_id(server_id, ctx):
        logger.debug('Invalid server ID')
        return

    # check if server is already stopped
    if not is_server_running(server_id, ctx):
        await ctx.reply('Server already stopped')
        logger.debug('Server already stopped')
        return

    # check if player is online
    player_count = get_player_count(server_id, ctx)
    if player_count != 0:
        await ctx.reply(f'cannot stop server: {player_count} Player(s) online')
        logger.debug(f'cannot stop server: {player_count} Player(s) online')
        return

    if stop_server(server_id):
        await ctx.reply('Server stopped')
        logger.debug('Server stopped')
    else:
        await ctx.reply('failed to stop server')
        logger.debug('failed to stop server')


# restart a server
@bot.hybrid_command(name='restart', description='restart a server')
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.autocomplete(server_id=get_server_list)
async def restart(ctx, server_id):
    logger.debug('restart')

    if not await check_server_id(server_id, ctx):
        logger.debug('Invalid server ID')
        return

    # check if server is already stopped
    if not is_server_running(server_id, ctx):
        await ctx.reply('Server already stopped')
        logger.debug('Server already stopped')
        return

    # check if player is online
    player_count = get_player_count(server_id, ctx)
    if player_count != 0:
        await ctx.reply(f'cannot restart server: {player_count} Player(s) online')
        logger.debug(f'cannot restart server: {player_count} Player(s) online')
        return

    if stop_server(server_id):
        await ctx.reply('Server stopped')
        logger.debug('Server stopped')
    else:
        await ctx.reply('failed to stop server')
        logger.debug('failed to stop server')

    data = get_json_response(API_ENDPOINT + str(server_id) + '/action/restart_server',
                             'failed to restart server', method=HttpMethod.POST)
    if not data:
        await ctx.reply('failed to start server')
        logger.debug('failed to start server (data is None)')
        return

    if data['status'] == "ok":
        await ctx.reply('Server restarted')
        logger.debug('Server restarted')


# command not found
@bot.event
async def on_command_error(ctx, error):
    """
    Handle command errors
    """
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found. Use `>help` to get a list of available commands.')
        logger.debug(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Missing required argument. Use `>help` to get a list of available commands.')
        logger.debug(error)


bot.run(os.environ['DISCORD_TOKEN'])
