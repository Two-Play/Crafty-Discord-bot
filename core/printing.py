"""
This module contains functions to print the server information as text.
"""
import logging

logger = logging.getLogger('CraftyDiscordBot')



def print_server_info(data) -> str:
    """
    Print the server information as text.
    """
    # Extract server names, server IPs and server ports from the API response
    server_info = [(server.get('server_id', '-'),
                    server.get('server_name', ''),
                    server.get('server_ip', 'unknown'),
                    server.get('server_port', 'unknown')) for server in data['data']]

    # Format the server information as text
    server_info_text = ""
    for server_id, name, ip, port in server_info:
        server_info_text += f"```\nID: {server_id}\nServer: {name}\n  IP: {ip}\n  Port: {port}\n```\n"
    return server_info_text


def print_server_status(data) -> str:
    """
    Print the server status as text.
    """
    data = data['data']

    cpu_usage = data['cpu']
    mem = data['mem']
    mem_percent = data['mem_percent']
    running = data['running']

    server_info_text: str
    if running:
        server_info_text = (
            f"```\nWorld: {data['world_name']}\nRunning: {running}\nPlayers: {data['players']}\n"
            f"Version: {data['version']}\nCPU: {cpu_usage}%\nRAM: {mem}MB ({mem_percent}%)\n```\n"
        )
    else:
        server_info_text = f"```\nWorld: {data['world_name']}\nRunning: {running}\n```\n"
    return server_info_text
