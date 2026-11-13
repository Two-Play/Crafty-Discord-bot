# Crafty Controller Discord bot

![GitHub License](https://img.shields.io/github/license/Two-Play/Crafty-Discord-bot)
![GitHub top language](https://img.shields.io/github/languages/top/Two-Play/Crafty-Discord-bot)
![GitHub contributors](https://img.shields.io/github/contributors/Two-Play/Crafty-Discord-bot)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/d5b3f979005e4c52916f7fb741068483)](https://app.codacy.com/gh/Two-Play/Crafty-Discord-bot/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/d5b3f979005e4c52916f7fb741068483)](https://app.codacy.com/gh/Two-Play/Crafty-Discord-bot/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_coverage)

A Discord bot that controls Minecraft servers managed by [Crafty Controller 4](https://craftycontrol.com/). Friends
can list, start, stop and restart servers from Discord without access to the Crafty panel.

> [!WARNING]
> This project is still in development. Use it at your own risk.

**📖 The full documentation is in the [wiki](https://github.com/Two-Play/Crafty-Discord-bot/wiki).**

## Features

- **Server list and status**: players, version, CPU and RAM of every server
- **Start, stop, restart**: stop and restart are refused while players are online
- **Backups**: start Crafty backups (bot owner only)
- **Slash commands** with autocomplete for servers and backups, or the `>` prefix
- **Auto stop**: stop servers that have been empty for a full interval
- **Web dashboard**: bot and server status, feature flags to switch commands on and off, and the live log

## Quick start

1. Create a Crafty API token and a Discord bot: [Installation](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Installation)
2. Run the bot:

   ```bash
   docker run -d --name crafty-bot --restart unless-stopped \
     -e DISCORD_TOKEN=YOUR_DISCORD_TOKEN \
     -e CRAFTY_TOKEN=YOUR_CRAFTY_TOKEN \
     -e SERVER_URL=https://YOUR-CRAFTY-HOST:8443 \
     -v crafty-bot-data:/usr/src/app/data \
     twoplay/craftybot:latest
   ```

3. Type `>help` in Discord. Run `>sync` once as the bot owner to enable the slash commands.

## Documentation

| Page | Content |
|------|---------|
| [Installation](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Installation) | Crafty user, Discord bot, Docker and Python setup |
| [Configuration](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Configuration) | All environment variables |
| [Commands](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Commands) | Discord commands and slash command setup |
| [Web Dashboard](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Web-Dashboard) | Status page, feature flags, logs and security |
| [Auto Stop](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Auto-Stop) | How servers without players are stopped |
| [Troubleshooting](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Troubleshooting) | Common problems and their fixes |
| [Development](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Development) | Tests, linters and contributing |

## Roadmap

- **Web dashboard controls**: start, stop and back up servers from the dashboard

## Issues and contributing

Please report bugs and ideas in the [issue tracker](https://github.com/Two-Play/Crafty-Discord-bot/issues). Pull
requests are welcome: create a branch from `develop`, add tests, and open the pull request against `develop`. See
[Development](https://github.com/Two-Play/Crafty-Discord-bot/wiki/Development) for the setup.

## Support the project

You can support the project by giving it a star, sharing it, contributing, or with a donation:

| Platform | Link | QR Code |
|----------|------|---------|
| ![Buy Me A Coffee Badge](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FD0?logo=buymeacoffee&logoColor=000&style=for-the-badge) | [Buy Me a Coffee](https://www.buymeacoffee.com/TwoPlay) | ![Buy Me a Coffee QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=https://www.buymeacoffee.com/TwoPlay&qzone=1&margin=0&size=150x150&ecc=L) |
| ![PayPal Badge](https://img.shields.io/badge/PayPal-003087?logo=paypal&logoColor=fff&style=for-the-badge) | [PayPal](https://www.paypal.com/donate/?hosted_button_id=RQAUT43DDLTJG) | ![PayPal QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=https://www.paypal.com/donate/?hosted_button_id=RQAUT43DDLTJG&qzone=1&margin=0&size=150x150&ecc=L) |

## License

This project is licensed under the MIT License, see [LICENSE.md](LICENSE.md).
