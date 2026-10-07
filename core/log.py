"""
Logging setup of the bot.

All output goes through the root logger. ``LOG_LEVEL`` controls the loggers of the
bot itself (``core.*``). Third-party libraries (discord.py, requests, urllib3...) never
log below INFO, because their DEBUG output is extremely verbose and can contain
message contents and request payloads.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import List, Optional, Union

LOG_FORMAT = '%(asctime)s - [%(name)s] - [%(levelname)s] -> %(message)s'
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 3

APP_LOGGER = 'core'


def setup_logging(level: Union[int, str] = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    Configure the root logger. Can be called again to change the configuration.

    Args:
        level: Level of the bot loggers (``core.*``).
        log_file: Optional path of a file the log is written to in addition to stderr.
            The file is rotated at 5 MB, three old files are kept.
    """
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())

    formatter = logging.Formatter(LOG_FORMAT)
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            log_file, maxBytes=LOG_FILE_MAX_BYTES, backupCount=LOG_FILE_BACKUP_COUNT, encoding='utf-8'))

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)

    root.setLevel(max(level, logging.INFO))
    logging.getLogger(APP_LOGGER).setLevel(level)
