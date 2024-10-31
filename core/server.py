"""This module contains the Server class."""

from core.constants import API_ENDPOINT
from core.network import get_json_response


def stop_server(server_id) -> bool:
    """
    Stop the server with the specified ID.
    """
    data = get_json_response(API_ENDPOINT + str(server_id) + '/action/stop_server',
                             'failed to stop server')
    if data['status'] == "ok":
        print('Server stopped', str(server_id))
        return True

    print('failed to stop server')
    return False


def get_player_count(server_id, ctx=None) -> int:
    """
    Get the number of players online on the server with the specified server ID.
    """
    data = get_json_response(API_ENDPOINT + str(server_id) +
                             '/stats', 'failed to get server stats')
    if not data:
        if ctx:
            ctx.reply('failed to get server stats')
        return -1
    return data['data']['online']


def is_server_running(server_id, ctx=None) -> bool:
    """
    Check if the server with the specified ID is running.
    """
    data = get_json_response(API_ENDPOINT + str(server_id) +
                             '/stats', 'failed to get server stats')
    if not data:
        if ctx:
            ctx.reply('failed to get server stats')
        return False
    return data['data']['running']
