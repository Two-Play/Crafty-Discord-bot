import asyncio
import os
from typing import List

import requests
import discord
from discord.ext import commands
from discord import Interaction, app_commands
from discord.ext.commands import is_owner
from discord import ui


def check():
    # check if all environment variables are set
    if 'SERVER_URL' in os.environ and 'USERNAME' in os.environ and 'PASSWORD' in os.environ and 'DISCORD_TOKEN' in os.environ and 'CRAFTY_TOKEN' in os.environ:
        print('All environment variables set')
        if os.environ['SERVER_URL'] == '':
            print('SERVER_URL not set')
            exit()
        if os.environ['CRAFTY_TOKEN'] == '':
            if os.environ['USERNAME'] == '':
                print('USERNAME not set')
                exit()
            if os.environ['PASSWORD'] == '':
                print('PASSWORD not set')
                exit()
            else:
                print('CRAFTY_TOKEN not set')

        if os.environ['DISCORD_TOKEN'] == '':
            print('DISCORD_TOKEN not set')
            exit()

    else:
        print('Not all environment variables set')
        exit()


check()

SERVER_URL = os.environ['SERVER_URL']
USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)


# stop server after 1 hour of inactivity (no players online)
async def auto_stop():
    while True:

        running_server_ids = []

        # get list of servers ids and loop through them and add only the ones that are running
        response = requests.get(SERVER_URL + '/api/v2/servers',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            data = response.json()
            server_ids = [server['server_id'] for server in data['data']]

            for server_id in server_ids:
                response = requests.get(SERVER_URL + '/api/v2/servers/' + str(server_id) + '/stats',
                                        headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
                if response.status_code == 200:
                    if response.json()['data']['running']:
                        running_server_ids.append(server_id)
                else:
                    print('failed to get server stats')

            # loop through the running servers and check if there are players online
            for running_server_id in running_server_ids:
                response = requests.get(SERVER_URL + '/api/v2/servers/' + str(running_server_id) + '/stats',
                                        headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
                if response.status_code == 200:
                    if response.json()['data']['online'] == 0:
                        response = requests.post(
                            SERVER_URL + '/api/v2/servers/' + str(running_server_id) + '/action/stop_server',
                            headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']},
                            verify=False)
                        if response.status_code == 200:
                            if response.json()['status'] == "ok":
                                print('Server stopped', str(running_server_id))
                            else:
                                print('failed to stop server')
                        else:
                            print('failed to stop server')
                    # else:
                    #   print('{} Player(s) online on {}'.format(response.json()['data']['online'], str(running_server_id)))
                else:
                    print('failed to get server stats')
        else:
            print('failed to get server list')

        await asyncio.sleep(3600)  # task runs every hour


@bot.event
async def on_ready():
    print('Bot is ready. {}'.format(bot.user))

    await auto_stop()
    # response = requests.post(SERVER_URL + '/api/v2/auth/login', json={'username': USERNAME, 'password': PASSWORD}, verify=False)
    # if response.status_code == 200:
    #    os.environ['CRAFTY_TOKEN'] = response.json()['data']['token']
    # else:
    #    print('Login failed', response.status_code)


"""
@bot.tree.command(name="rps")/*
@app_commands.guilds(discord.Object(id=1190285247288447026))
@app_commands.choices(choices=[
    app_commands.Choice(name="Rock", value="rock"),
    app_commands.Choice(name="Paper", value="paper"),
    app_commands.Choice(name="Scissors", value="scissors"),
    ])
async def rps(i: discord.Interaction, choices: app_commands.Choice[str]):
    if (choices.value == 'rock'):
        counter = 'paper'
    elif (choices.value == 'paper'):
        counter = 'scissors'
    else:
        counter = 'rock'
"""


@bot.hybrid_command(name='sync', description='Sync commands')
@app_commands.guilds(discord.Object(id=1190285247288447026))
@is_owner()
async def sync(ctx) -> None:
    synced = await bot.tree.sync(guild=discord.Object(id=1190285247288447026))
    # add commands to the appcommands
    await ctx.reply("{} commands synced".format(len(synced)))


# @bot.hybrid_command(name='ping', description='Pong!')
# @app_commands.guilds(discord.Object(id=1190285247288447026))
# async def ping(ctx, nummer: int):
#     print('ping')
#     await ctx.send('Pong! ' + str(nummer))


# get new token
async def get_token(ctx):
    print('get_token')
    response = requests.post(SERVER_URL + '/api/v2/auth/login', json={'username': USERNAME, 'password': PASSWORD},
                             verify=False)
    if response.status_code == 200:
        os.environ['CRAFTY_TOKEN'] = response.json()['data']['token']
        await ctx.send('Toke successful retrieved')
        return True
    else:
        print('Login failed', response.status_code)
        return False


@bot.hybrid_command(name='login', description='get login status')
@app_commands.guilds(discord.Object(id=1190285247288447026))
# login to the server
async def login(ctx):
    print('login')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.reply('login failed')
    else:
        await ctx.reply('login successful')


@bot.hybrid_command(name='list', description='get server list')
@app_commands.guilds(discord.Object(id=1190285247288447026))
# get the list of servers
async def list(ctx):
    print('servers')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.reply('login failed')
    else:
        response = requests.get(SERVER_URL + '/api/v2/servers',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            # print(json.dumps(response.json(), indent=4))

            data = response.json()
            # Extrahiere Servernamen, Server-IPs und Server-Ports aus der API-Antwort
            server_info = [(server['server_id'], server['server_name'], server['server_ip'], server['server_port']) for
                           server in
                           data['data']]

            # Formatiere die Serverinformationen als Text
            server_info_text = ""
            for id, name, ip, port in server_info:
                server_info_text += f"```\nID: {id}\nServer: {name}\n  IP: {ip}\n  Port: {port}\n```\n"

            await ctx.reply(f"Serverinformationen:\n{server_info_text}")

        else:
            await ctx.reply('failed to get server list')


# get statistics of a server
@bot.hybrid_command(name='stats', description='get server stats')
@app_commands.guilds(discord.Object(id=1190285247288447026))
async def stats(ctx, server_id):
    print('stats')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.reply('login failed')
    else:
        response = requests.get(SERVER_URL + '/api/v2/servers/' + str(server_id) + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            # print(json.dumps(response.json(), indent=4))

            data = response.json()['data']
            # Extrahiere Servernamen, Server-IPs und Server-Ports aus der API-Antwort
            # server_info = [data['world_name'], data['running'], data['players'], data['version']]

            # Formatiere die Serverinformationen als Text
            cpu_usage = data['cpu']
            mem = data['mem']
            mem_percent = data['mem_percent']
            running = data['running']

            server_info_text: str
            if running:
                server_info_text = (
                    f"```\nWorld: {data['world_name']}\nRunning: {running}\nPlayers: {data['players']}\nVersion: {data['version']}\nCPU: {cpu_usage}%\nRAM: {mem}MB ({mem_percent}%)\n```\n")
            else:
                server_info_text = (f"```\nWorld: {data['world_name']}\nRunning: {running}\n```\n")

            # server_info_text = (f"```\nWorld: {data['world_name']}\nRunning: {running}\nPlayers: {data['players'] if running else 'N/A'}\nVersion: "
            #                     f"{data['version'] if running else 'N/A'}\n```\n")
            await ctx.reply(f"Serverinformationen:\n{server_info_text}")
        else:
            await ctx.reply('failed to get server list')


# start a server
@bot.hybrid_command(name='start', description='start a server')
@app_commands.guilds(discord.Object(id=1190285247288447026))
async def start(ctx, server_id):
    print('start')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.reply('login failed')
    else:
        # check if server is already running
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['data']['running']:
                await ctx.reply('Server already running')
                return
        else:
            await ctx.reply('failed to get server stats')
            return
        response = requests.post(SERVER_URL + '/api/v2/servers/' + server_id + '/action/start_server',
                                 headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['status'] == "ok":
                await ctx.reply('Server started')
            else:
                await ctx.reply('failed to start server')
        else:
            await ctx.reply('failed to start server')


# stop a server
@bot.hybrid_command(name='stop', description='stop a server')
@app_commands.guilds(discord.Object(id=1190285247288447026))
async def stop(ctx, server_id):
    print('stop')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.reply('login failed')
    else:
        # check if server is already stopped
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if not response.json()['data']['running']:
                await ctx.reply('Server already stopped')
                return
        else:
            await ctx.reply('failed to get server stats')
            return

        # check if player is online
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['data']['online'] != 0:
                await ctx.reply('cannot stop server: {} Player(s) online'.format(response.json()['data']['online']))
                return
        else:
            await ctx.reply('failed to get server stats')
            return

        response = requests.post(SERVER_URL + '/api/v2/servers/' + server_id + '/action/stop_server',
                                 headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['status'] == "ok":
                await ctx.reply('Server stopped')
            else:
                await ctx.reply('failed to stop server')
        else:
            await ctx.reply('failed to stop server')


# show help
# @bot.command()
# @bot.tree.command(name='bot_help', description='Show help')
@bot.hybrid_command(name='bot_help', description='Show help')
@app_commands.guilds(discord.Object(id=1190285247288447026))
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
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found. Use `>bot_help` to get a list of available commands.')


bot.run(os.environ['DISCORD_TOKEN'])
