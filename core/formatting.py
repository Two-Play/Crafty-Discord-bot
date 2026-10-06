"""
Functions to format Crafty API data as Discord message text.
"""

from typing import Any, Dict, Iterable


def format_server_list(servers: Iterable[Dict[str, Any]]) -> str:
    """
    Format a list of servers (ID, name, IP and port) as code blocks.
    """
    return ''.join(
        f"```\nID: {server.get('server_id', '-')}\n"
        f"Server: {server.get('server_name', '')}\n"
        f"  IP: {server.get('server_ip', 'unknown')}\n"
        f"  Port: {server.get('server_port', 'unknown')}\n```\n"
        for server in servers
    )


def format_server_stats(stats: Dict[str, Any]) -> str:
    """
    Format the statistics of a server as a code block.

    Players, version, CPU and RAM are only shown while the server is running.
    """
    world = stats.get('world_name', 'unknown')
    running = stats.get('running', False)
    if not running:
        return f"```\nWorld: {world}\nRunning: {running}\n```\n"

    return (
        f"```\nWorld: {world}\nRunning: {running}\nPlayers: {stats.get('players', 'unknown')}\n"
        f"Version: {stats.get('version', 'unknown')}\nCPU: {stats.get('cpu', '?')}%\n"
        f"RAM: {stats.get('mem', '?')}MB ({stats.get('mem_percent', '?')}%)\n```\n"
    )
