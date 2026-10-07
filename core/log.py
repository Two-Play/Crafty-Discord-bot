"""
Logging setup of the bot.

All output goes through the root logger. ``LOG_LEVEL`` controls the loggers of the
bot itself (``core.*``). Third-party libraries (discord.py, requests, urllib3...) never
log below INFO, because their DEBUG output is extremely verbose and can contain
message contents and request payloads.
"""

from __future__ import annotations

import itertools
import logging
import logging.handlers
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Union

LOG_FORMAT = '%(asctime)s - [%(name)s] - [%(levelname)s] -> %(message)s'
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 3

LOG_BUFFER_SIZE = 1000
LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR')

APP_LOGGER = 'core'


class LogBuffer(logging.Handler):
    """Keeps the most recent log records in memory, for the web dashboard."""

    def __init__(self, capacity: int = LOG_BUFFER_SIZE):
        super().__init__()
        self._entries: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self._ids = itertools.count(1)
        self._formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            if record.exc_info:
                message += '\n' + self._formatter.formatException(record.exc_info)
            elif record.exc_text:
                message += '\n' + record.exc_text
            entry = {
                'id': next(self._ids),
                'time': datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec='milliseconds'),
                'level': record.levelname,
                'logger': record.name,
                'message': message,
            }
        except Exception:  # pylint: disable=broad-exception-caught
            self.handleError(record)
            return
        self._entries.append(entry)

    def entries(self, after: int = 0, limit: int = LOG_BUFFER_SIZE) -> List[Dict[str, Any]]:
        """Return the entries with an ID greater than ``after``, at most the last ``limit`` ones."""
        with self.lock:  # emit() runs under this lock too, which keeps the deque consistent
            entries = [entry for entry in self._entries if entry['id'] > after]
        return entries[-limit:] if limit > 0 else []


LOG_BUFFER = LogBuffer()


def set_log_level(level: Union[int, str]) -> None:
    """Change the level of the bot loggers at runtime. Libraries never go below INFO."""
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
    if not isinstance(level, int):
        raise ValueError(f'Invalid log level {level!r}')
    logging.getLogger().setLevel(max(level, logging.INFO))
    logging.getLogger(APP_LOGGER).setLevel(level)


def get_log_level() -> str:
    """Return the name of the current level of the bot loggers."""
    return logging.getLevelName(logging.getLogger(APP_LOGGER).getEffectiveLevel())


def setup_logging(level: Union[int, str] = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Configure the root logger. Can be called again to change the configuration.

    Besides stderr (and the optional file), every record goes to ``LOG_BUFFER``, which the
    web dashboard shows.

    Args:
        level: Level of the bot loggers (``core.*``).
        log_file: Optional path of a file the log is written to in addition to stderr.
            The file is rotated at 5 MB, three old files are kept.
    """
    formatter = logging.Formatter(LOG_FORMAT)
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            log_file, maxBytes=LOG_FILE_MAX_BYTES, backupCount=LOG_FILE_BACKUP_COUNT, encoding='utf-8'))

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        if handler is not LOG_BUFFER:  # keep the buffer and its entries across reconfigurations
            handler.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.addHandler(LOG_BUFFER)

    set_log_level(level)
