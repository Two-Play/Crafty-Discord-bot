"""
Functions to format Crafty API data as Discord message text.
"""

from typing import Any, Dict, Iterable

from core.crafty import busy_state, player_count, player_names


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


def format_memory(value: Any) -> str:
    """Format the memory usage, which Crafty reports in bytes, e.g. ``1.5 GB``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value) if value not in (None, '') else '?'
    size = float(value)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(size) < 1024:
            return f'{size:.0f} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


def format_players(stats: Dict[str, Any]) -> str:
    """Format the player count with the maximum and the player names, e.g. ``2/20 (Steve, Alex)``."""
    count = player_count(stats)
    if count is None:
        return 'unknown (Crafty cannot ping the server)'

    max_players = stats.get('max')
    text = f'{count}/{max_players}' if max_players else str(count)
    names = player_names(stats)
    if names:
        text += f" ({', '.join(names)})"
    return text


def format_server_stats(stats: Dict[str, Any]) -> str:
    """
    Format the statistics of a server as a code block.

    Players, version, CPU and RAM are only shown while the server is running.
    """
    world = stats.get('world_name') or 'unknown'
    running = bool(stats.get('running', False))
    lines = [f'World: {world}', f'Running: {running}']
    state = busy_state(stats)
    if state:
        lines.append(f'Status: {state}')
    elif stats.get('crashed'):
        lines.append('Status: crashed')

    if running:
        version = stats.get('version')
        if not version or version == 'False':
            version = 'unknown'
        lines += [
            f'Players: {format_players(stats)}',
            f'Version: {version}',
            f"CPU: {stats.get('cpu', '?')}%",
            f"RAM: {format_memory(stats.get('mem'))} ({stats.get('mem_percent', '?')}%)",
        ]
    return '```\n' + '\n'.join(lines) + '\n```\n'
