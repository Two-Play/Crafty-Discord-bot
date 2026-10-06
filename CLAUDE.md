# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Discord bot (discord.py) that controls Minecraft servers managed by Crafty Controller 4 through its REST API (`/api/v2/...`). The version is set in `core/__init__.py` (`__version__`). Python 3.10+ is required (CI uses 3.10 and the Docker image uses 3.12).

## Commands

```bash
pip install -r requirements-dev.txt      # runtime deps (requirements.txt) + coverage/flake8/pylint
cp .env.example .env                     # then fill in SERVER_URL, DISCORD_TOKEN, CRAFTY_TOKEN

python -m core                           # run the bot (python core/main.py also works; Docker uses -m core)

python -m unittest                       # all tests (run from repo root)
python -m unittest tests.test_servers_cog                                   # one module
python -m unittest tests.test_servers_cog.TestServerCommands.test_start     # one test
coverage run -m unittest && coverage report

flake8 core tests                        # config in .flake8 (max line length 120)
pylint core                              # config in pyproject.toml
```

CI (`.github/workflows/pylint-tests.yml`) runs flake8 and pylint with `--exit-zero`, so only test failures fail the build. The code is currently clean under both linters, so keep it that way. Coverage is uploaded to Codacy. Pushing a tag triggers the release and Docker publish workflows (image `twoplay/craftybot`).

Branching: work on feature branches created from `develop`, then merge them back into `develop`. `master` is the release branch.

## Architecture

All code lives in the `core` package.

- **`main.py`**: the entry point. `main()` loads `.env`, builds `Settings`, and creates `CraftyClient` and `CraftyBot`. It exits with code 1 if the config is invalid. Logging goes through the root logger (`logging.basicConfig`), and `bot.run(..., log_handler=None)` lets discord.py log through it as well. Modules use `logging.getLogger(__name__)`.
- **`config.py`**: `Settings.from_env()` is the only place that reads environment variables. It raises `ConfigError` instead of exiting. Secrets are excluded from `repr`. Pass a dict to `from_env` in tests.
- **`crafty.py`**: `CraftyClient` is the only HTTP layer. It uses a `requests.Session`, and every public method is a coroutine that runs the blocking request with `asyncio.to_thread` so it doesn't block the event loop. **Any failure raises `CraftyAPIError`**: network errors, non-2xx responses, invalid JSON, or a body whose `status` isn't `"ok"`. Methods return the unwrapped `data` field. `parse_server_id` validates server UUIDs and returns them in canonical form.
- **`bot.py`**: `CraftyBot(commands.Bot)`. Its `setup_hook` logs in with username and password when no token is set, adds the cogs, and copies global app commands to `GUILD_ID` when one is set. `on_command_error` is the **single error handler**: it unwraps `CommandInvokeError`/`HybridCommandError` and turns `CraftyAPIError`, `BadArgument`, `CheckFailure` and similar errors into user-facing messages. Commands should simply let `CraftyAPIError` propagate.
- **`cogs/servers.py`**: `list`, `stats`, `start`, `stop` and `restart` as `hybrid_command`s, so each works with the `>` prefix and as a slash command. The `ServerId` converter validates IDs, `server_autocomplete` caches the server list for 60 seconds, and `cog_before_invoke` defers the interaction because Crafty calls can exceed Discord's 3-second limit.
- **`cogs/admin.py`**: owner-only commands `sync`, `clear`, `commands` and `get_token`. Slash commands only appear in Discord after an owner runs `>sync`.
- **`cogs/auto_stop.py`**: a `tasks.loop` (only loaded when `ENABLE_AUTO_STOP_SERVER=true`) that stops running servers with 0 players every `AUTO_STOP_SLEEP_TIME` seconds. Errors are logged, and the loop keeps running.
- **`formatting.py`**: turns Crafty data into Discord code-block text. **`help_command.py`**: the `>help` output.

## Tests

The tests use `unittest`, with `IsolatedAsyncioTestCase` for async code. Cog commands are tested by calling `cog.<command>.callback(cog, ctx, ...)` with a `MagicMock` ctx whose `reply` is an `AsyncMock`, and a mocked `CraftyClient`. `CraftyClient` itself is tested by injecting a mocked `session`. Use `assertLogs` for code paths that log warnings so the test output stays clean.

`core/main.py` loads the real `.env` from the repo root. To try the startup path without connecting to Discord, force a config error (e.g. `AUTO_STOP_SLEEP_TIME=0 python -m core`).
