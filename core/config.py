"""
Configuration of the bot, loaded from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Tuple

DEFAULT_AUTO_STOP_INTERVAL = 1800  # seconds (30 minutes)
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_WEB_HOST = '127.0.0.1'
DEFAULT_WEB_PORT = 8080
DEFAULT_FLAGS_FILE = 'data/feature_flags.json'
LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR')

# Relative paths in the settings are resolved against the project directory (where .env lives),
# not the working directory, so the bot finds its files wherever it is started from.
BASE_DIR = Path(__file__).resolve().parent.parent

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


def _resolve_path(value: str) -> str:
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else BASE_DIR / path)


def _get_list(env: Mapping[str, str], name: str) -> Tuple[str, ...]:
    return tuple(item.strip().lower() for item in _get(env, name).split(',') if item.strip())


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
    web_enabled: bool = False
    web_host: str = DEFAULT_WEB_HOST
    web_port: int = DEFAULT_WEB_PORT
    web_password: str = field(default='', repr=False)
    web_allowed_hosts: Tuple[str, ...] = ()
    flags_file: str = str(BASE_DIR / DEFAULT_FLAGS_FILE)

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
        if log_level not in LOG_LEVELS:
            raise ConfigError(f"LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}, got {log_level!r}")

        web_port = _get_int(env, 'WEB_PORT', DEFAULT_WEB_PORT)
        if not 0 < web_port < 65536:
            raise ConfigError('WEB_PORT must be between 1 and 65535')

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
            log_file=_resolve_path(_get(env, 'LOG_FILE')) if _get(env, 'LOG_FILE') else None,
            web_enabled=_get_bool(env, 'WEB_ENABLED'),
            web_host=_get(env, 'WEB_HOST') or DEFAULT_WEB_HOST,
            web_port=web_port,
            web_password=_get(env, 'WEB_PASSWORD'),
            web_allowed_hosts=_get_list(env, 'WEB_ALLOWED_HOSTS'),
            flags_file=_resolve_path(_get(env, 'FLAGS_FILE') or DEFAULT_FLAGS_FILE),
        )
