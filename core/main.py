"""
Entry point of the bot. Run with ``python -m core`` (or ``python core/main.py``).
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

if not __package__:
    # Started as a script (python core/main.py): make the `core` package importable.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable=wrong-import-position
from core.bot import CraftyBot  # noqa: E402
from core.config import ConfigError, Settings  # noqa: E402
from core.crafty import CraftyClient  # noqa: E402

logger = logging.getLogger('core')

LOG_FORMAT = '%(asctime)s - [%(name)s] - [%(levelname)s] -> %(message)s'


def main() -> int:
    """Load the configuration and run the bot. Returns the process exit code."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    load_dotenv()

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        logger.error('%s', exc)
        return 1
    logging.getLogger().setLevel(settings.log_level)

    crafty = CraftyClient(settings.server_url, settings.crafty_token, verify_ssl=settings.verify_ssl)
    bot = CraftyBot(settings, crafty)
    bot.run(settings.discord_token, log_handler=None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
