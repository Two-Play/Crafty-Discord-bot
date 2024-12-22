"""
This module contains helper different functions.
"""
import logging
import os
import sys
import time
import uuid

import discord
from discord import app_commands

from core.network import get_json_response

logger = logging.getLogger('CraftyDiscordBot')

def check_env_vars():
    """
    Check if all required environment variables are set and exit if any are missing.

    The required environment variables are:
    - SERVER_URL
    - DISCORD_TOKEN
    - CRAFTY_TOKEN (or USERNAME and PASSWORD if CRAFTY_TOKEN is not set)

    If any required environment variable is missing or empty, the function will
    print an error message and exit the program.
    """
    required_env_vars = [
        var for var in ['SERVER_URL', 'DISCORD_TOKEN']
        if var not in os.environ
    ]

    if 'CRAFTY_TOKEN' not in os.environ or not os.environ['CRAFTY_TOKEN']:
        required_env_vars.extend(
            var for var in ['USERNAME', 'PASSWORD']
            if var not in os.environ
        )
        required_env_vars.append('or CRAFTY_TOKEN')

    if required_env_vars:
        logger.info('Not all environment variables set')
        for env_var in required_env_vars:
            logger.info(f'{env_var} not set')
        sys.exit()

    logger.info('All environment variables set')

    for var in ['SERVER_URL', 'CRAFTY_TOKEN', 'DISCORD_TOKEN']:
        if not os.environ.get(var):
            logger.info(f'{var} not set')
            sys.exit()


async def check_server_id(server_id: str, ctx=None) -> bool:
    """
    Check if the server ID is valid.

    Args:
        server_id (str): The server ID to check.
        ctx (commands.Context): The context of the command.

    Returns:
        bool: True if the server ID is valid, False otherwise.
    """

    try:
        logger.debug('Checking server ID')
        uuid.UUID(server_id, version=4)
    except ValueError:
        logger.debug('Invalid server ID')
        if ctx:
            await ctx.reply('Invalid server ID')
        return False
    logger.debug('Valid server ID')
    return True


# Global variables for caching
cached_server_list = None
cache_timestamp = 0
CACHE_DURATION = 60  # Cache duration in seconds (e.g., 1 minute)


async def get_server_list(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    global cached_server_list, cache_timestamp

    # Check if the cache is still valid
    if cached_server_list is not None and (time.time() - cache_timestamp) < CACHE_DURATION:
        data = cached_server_list
    else:
        data = get_json_response('/api/v2/servers', 'failed to get server list')
        if not data:
            return [app_commands.Choice(name='failed to get server list', value='failed to get server list')]
        cached_server_list = data
        cache_timestamp = time.time()

    data = data['data']
    server_uuid = []
    server_name = []
    for server in data:
        server_uuid.append(server['server_id'])
        server_name.append(server['server_name'])
    server_list = [app_commands.Choice(name=server_name[i], value=server_uuid[i]) for i in range(len(server_uuid)) if
                   server_name[i].lower().startswith(current.lower())]
    return server_list
