"""
Entry point of the bot. Run with ``python -m core`` (or ``python core/main.py``).
"""

import logging
import sys
from pathlib import Path

import discord
from dotenv import load_dotenv

if not __package__:
    # Started as a script (python core/main.py): make the `core` package importable.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable=wrong-import-position
from core import __version__  # noqa: E402
from core.bot import CraftyBot  # noqa: E402
from core.config import ConfigError, Settings  # noqa: E402
from core.crafty import CraftyClient  # noqa: E402
from core.log import setup_logging  # noqa: E402

logger = logging.getLogger('core.main')


def main() -> int:
    """Load the configuration and run the bot. Returns the process exit code."""
    setup_logging()
    load_dotenv()

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        logger.error('Invalid configuration: %s', exc)
        return 1

    try:
        setup_logging(settings.log_level, settings.log_file)
    except OSError as exc:
        logger.error('Cannot open log file %s: %s', settings.log_file, exc)
        return 1

    logger.info('Starting Crafty Bot %s', __version__)
    logger.debug('Settings: %r', settings)

    crafty = CraftyClient(settings.server_url, settings.crafty_token, verify_ssl=settings.verify_ssl)
    bot = CraftyBot(settings, crafty)
    try:
        bot.run(settings.discord_token, log_handler=None)
    except discord.LoginFailure as exc:
        logger.error('Login to Discord failed, check DISCORD_TOKEN: %s', exc)
        return 1
    except discord.PrivilegedIntentsRequired:
        logger.error('Enable the "Message Content Intent" of the bot in the Discord developer portal')
        return 1
    logger.info('Bot stopped')
    return 0


if __name__ == '__main__':
    sys.exit(main())
