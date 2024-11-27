"""
This module contains helper different functions.
"""

import os
import sys

from discord.app_commands import commands


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
        print('Not all environment variables set')
        for env_var in required_env_vars:
            print(f'{env_var} not set')
        sys.exit()

    print('All environment variables set')

    for var in ['SERVER_URL', 'CRAFTY_TOKEN', 'DISCORD_TOKEN']:
        if not os.environ.get(var):
            print(f'{var} not set')
            sys.exit()

def check_server_id(server_id: str, ctx) -> bool:
    """
    Check if the server ID is valid.

    Args:
        server_id (str): The server ID to check.
        ctx (commands.Context): The context of the command.

    Returns:
        bool: True if the server ID is valid, False otherwise.
    """
    if not server_id.isdigit():
        ctx.reply('invalid server id format, must be a UUID')
        return False
    return True