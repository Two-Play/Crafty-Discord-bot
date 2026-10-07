"""
Configuration of the bot, loaded from environment variables.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

DEFAULT_AUTO_STOP_INTERVAL = 1800  # seconds (30 minutes)
DEFAULT_LOG_LEVEL = 'INFO'

_TRUE_VALUES = {'1', 'true', 'yes', 'on'}


class ConfigError(Exception):
    """Raised when the configuration is missing or invalid."""


def _get(env: Mapping[str, str], *names: str) -> str:
    """Return the first non-empty value of the given variable names."""
    for name in names:
        value = env.get(name, '').strip()
        if value:
            return value
    return ''


def _get_bool(env: Mapping[str, str], name: str) -> bool:
    return _get(env, name).lower() in _TRUE_VALUES


def _get_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _get(env, name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f'{name} must be an integer, got {raw!r}') from exc


@dataclass(frozen=True)
class Settings:  # pylint: disable=too-many-instance-attributes
    """
    Settings of the bot.

    Secrets are excluded from ``repr`` so the settings can be logged safely.
    """

    server_url: str
    discord_token: str = field(repr=False)
    crafty_token: str = field(default='', repr=False)
    crafty_username: str = ''
    crafty_password: str = field(default='', repr=False)
    guild_id: Optional[int] = None
    auto_stop_enabled: bool = False
    auto_stop_interval: int = DEFAULT_AUTO_STOP_INTERVAL
    verify_ssl: bool = False
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: Optional[str] = None

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> Settings:
        """
        Build the settings from environment variables.

        Required are ``SERVER_URL``, ``DISCORD_TOKEN`` and either ``CRAFTY_TOKEN``
        or ``CRAFTY_USERNAME`` and ``CRAFTY_PASSWORD`` (the legacy names
        ``USERNAME`` and ``PASSWORD`` are accepted as well).

        Raises:
            ConfigError: If a required variable is missing or a value is invalid.
        """
        env = os.environ if env is None else env

        missing = [name for name in ('SERVER_URL', 'DISCORD_TOKEN') if not _get(env, name)]
        crafty_token = _get(env, 'CRAFTY_TOKEN')
        username = _get(env, 'CRAFTY_USERNAME', 'USERNAME')
        password = _get(env, 'CRAFTY_PASSWORD', 'PASSWORD')
        if not crafty_token and not (username and password):
            missing.append('CRAFTY_TOKEN (or CRAFTY_USERNAME and CRAFTY_PASSWORD)')
        if missing:
            raise ConfigError('Missing environment variables: ' + ', '.join(missing))

        auto_stop_interval = _get_int(env, 'AUTO_STOP_SLEEP_TIME', DEFAULT_AUTO_STOP_INTERVAL)
        if auto_stop_interval <= 0:
            raise ConfigError('AUTO_STOP_SLEEP_TIME must be greater than 0')

        log_level = (_get(env, 'LOG_LEVEL') or DEFAULT_LOG_LEVEL).upper()
        if not isinstance(logging.getLevelName(log_level), int):
            raise ConfigError(f'LOG_LEVEL {log_level!r} is not a valid log level')

        return cls(
            server_url=_get(env, 'SERVER_URL').rstrip('/'),
            discord_token=_get(env, 'DISCORD_TOKEN'),
            crafty_token=crafty_token,
            crafty_username=username,
            crafty_password=password,
            guild_id=_get_int(env, 'GUILD_ID', 0) or None,
            auto_stop_enabled=_get_bool(env, 'ENABLE_AUTO_STOP_SERVER'),
            auto_stop_interval=auto_stop_interval,
            verify_ssl=_get_bool(env, 'CRAFTY_VERIFY_SSL'),
            log_level=log_level,
            log_file=_get(env, 'LOG_FILE') or None,
        )
