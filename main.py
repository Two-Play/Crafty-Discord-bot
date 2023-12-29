import os
import requests
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)

SERVER_URL = os.environ['SERVER_URL']
USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']

@bot.event
async def on_ready():
    print('Bot is ready. {}'.format(bot.user))

    # check if all environment variables are set
    if 'SERVER_URL' in os.environ and 'USERNAME' in os.environ and 'PASSWORD' in os.environ and 'DISCORD_TOKEN' in os.environ and 'CRAFTY_TOKEN' in os.environ:
        print('All environment variables set')
        if os.environ['SERVER_URL'] == '':
            print('SERVER_URL not set')
            return
        if os.environ['CRAFTY_TOKEN'] == '':
            if os.environ['USERNAME'] == '':
                print('USERNAME not set')
                return
            if os.environ['PASSWORD'] == '':
                print('PASSWORD not set')
                return
            else:
                print('CRAFTY_TOKEN not set')
                return
        if os.environ['DISCORD_TOKEN'] == '':
            print('DISCORD_TOKEN not set')
            return
    else:
        print('Not all environment variables set')
        await bot.close()
        exit()

    # response = requests.post(SERVER_URL + '/api/v2/auth/login', json={'username': USERNAME, 'password': PASSWORD}, verify=False)
    # if response.status_code == 200:
    #    os.environ['CRAFTY_TOKEN'] = response.json()['data']['token']
    # else:
    #    print('Login failed', response.status_code)


@bot.command()
async def ping(ctx):
    print('ping')
    await ctx.send('pong')


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


@bot.command()
# login to the server
async def login(ctx):
    print('login')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.send('login failed')
    else:
        await ctx.send('login successful')


@bot.command()
# get the list of servers
async def list(ctx):
    print('servers')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.send('login failed')
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

            await ctx.send(f"Serverinformationen:\n{server_info_text}")

        else:
            await ctx.send('failed to get server list')


# get statistics of a server
@bot.command()
async def stats(ctx, server_id):
    print('stats')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.send('login failed')
    else:
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            # print(json.dumps(response.json(), indent=4))

            data = response.json()['data']
            # Extrahiere Servernamen, Server-IPs und Server-Ports aus der API-Antwort
            # server_info = [data['world_name'], data['running'], data['players'], data['version']]

            # Formatiere die Serverinformationen als Text
            running = data['running']
            server_info_text = f"```\nWorld: {data['world_name']}\nRunning: {running}\nPlayers: {data['players'] if running else 'N/A'}\nVersion: {data['version'] if running else 'N/A'}\n```\n"

            await ctx.send(f"Serverinformationen:\n{server_info_text}")

        else:
            await ctx.send('failed to get server list')


# start a server
@bot.command()
async def start(ctx, server_id):
    print('start')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.send('login failed')
    else:
        # check if server is already running
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['data']['running']:
                await ctx.send('Server already running')
                return
        else:
            await ctx.send('failed to get server stats')
            return
        response = requests.post(SERVER_URL + '/api/v2/servers/' + server_id + '/action/start_server',
                                 headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['status'] == "ok":
                await ctx.send('Server started')
            else:
                await ctx.send('failed to start server')
        else:
            await ctx.send('failed to start server')


# stop a server
@bot.command()
async def stop(ctx, server_id):
    print('stop')
    if os.environ['CRAFTY_TOKEN'] == '':
        await ctx.send('login failed')
    else:
        # check if server is already stopped
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if not response.json()['data']['running']:
                await ctx.send('Server already stopped')
                return
        else:
            await ctx.send('failed to get server stats')
            return

        # check if player is online
        response = requests.get(SERVER_URL + '/api/v2/servers/' + server_id + '/stats',
                                headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['data']['online'] != 0:
                await ctx.send('cannot stop server: {} Player(s) online'.format(response.json()['data']['online']))
                return
        else:
            await ctx.send('failed to get server stats')
            return

        response = requests.post(SERVER_URL + '/api/v2/servers/' + server_id + '/action/stop_server',
                                 headers={'Authorization': 'Bearer ' + os.environ['CRAFTY_TOKEN']}, verify=False)
        if response.status_code == 200:
            if response.json()['status'] == "ok":
                await ctx.send('Server stopped')
            else:
                await ctx.send('failed to stop server')
        else:
            await ctx.send('failed to stop server')


# show help
@bot.command()
async def bot_help(ctx):
    print('help')

    help_text = """
    ```
    >list
    >stats <server_id>
    >start <server_id>
    >stop <server_id>
    ```
    """
    await ctx.send(help_text)


# command not found
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Command not found. Use `>bot_help` to get a list of available commands.')


bot.run(os.environ['DISCORD_TOKEN'])