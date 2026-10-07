# Crafty Controller Discord bot

![GitHub License](https://img.shields.io/github/license/Two-Play/Crafty-Discord-bot)
![GitHub top language](https://img.shields.io/github/languages/top/Two-Play/Crafty-Discord-bot)
![GitHub contributors](https://img.shields.io/github/contributors/Two-Play/Crafty-Discord-bot)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/d5b3f979005e4c52916f7fb741068483)](https://app.codacy.com/gh/Two-Play/Crafty-Discord-bot/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/d5b3f979005e4c52916f7fb741068483)](https://app.codacy.com/gh/Two-Play/Crafty-Discord-bot/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_coverage)

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Roadmap](#roadmap)
4. [Installation](#installation)
    - [Requirements](#requirements)
    - [Docker](#docker)
    - [Python](#python)
5. [Usage](#usage)
6. [Issues](#issues)
7. [Contributing](#contributing)
8. [Support the Project](#support-the-project)
9. [Donations](#donations)
10. [License](#license)

## Introduction

> [!WARNING]
> This project is still in development and is not yet ready for production use. Please use it at your own risk.

This is a Discord bot that is designed to control the Crafty-Controller-4 server. This is useful if friends want to
start a server and you want to control it from Discord.
The bot is written in Python and uses the Discord.py library to interact with the
Discord API.

### Features

- **Server Status**: Get the status of the server
- **Server Start**: Start the server
- **Server Stop**: Stop the server
- **Server Restart**: Restart the server
- **Server List**: Get a list of all servers
- **Server Backup**: Start a backup of a server (bot owner only)
- **Auto complete (slash commands)**: Auto complete the server and the backup name
- **Auto stop**: Stop servers without players automatically
- **Web dashboard**: Status page with the bot and server status
- **Feature flags**: Switch commands and auto stop on and off in the web dashboard

## Roadmap

- **Web dashboard controls**: Start, stop and back up servers from the dashboard

## Installation

To install the bot, you will need to have a few things set up first.

### Requirements

#### Server

You should have a Server to deploy this bot. You can use a VPS, local server or a Raspberry Pi.
You can also use your own computer, but it is not recommended for availability reasons.

#### Crafty Controller user

You will need to create a new user (recommended) on the Crafty Controller
server and obtain the user token. You can do this by following these steps:

1. Go to your Crafty Controller server
2. Click on the gear icon in the top right corner
3. Click on "add user" and enter a name for your user (for example, "Crafty Bot")
4. Fill in the required fields, select the desired permissions and click on "Save"
5. Click on the pencil icon next to the user you just created
6. Click on "API Key" and select the following permissions:
    - COMMANDS
    - TERMINAL
    - PLAYERS
    - BACKUP (only needed for the `backup` command)
7. Enter a name for your user token (for example, "Crafty Bot Token")
8. Click on "Create" to generate the user token
9. Save your user token in a safe place (you will need it later)

#### Discord Bot

You will need to create a new Discord bot and obtain a bot token. You can do this by following these steps:

> [!IMPORTANT]  
> I don't know if the permissions are correct, but you can try it out. If it doesn't work, please let me know.
> You can also use the "ALL" permission, but this is not recommended for security reasons.

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click on "New Application"
3. Enter a name for your bot (for example, "Crafty Bot")
4. Accept the terms and click on "Create"
5. If you want to add an icon to your bot, click on "General Information" in the left-hand menu and then click on "
   Upload Image" under "App Icon"
6. Click on "Bot" in the left-hand menu
7. Under "username", you can change the name of your bot if you wish
8. Disable the "Public Bot" option
9. Click on "Reset Token" and confirm by clicking on "Yes, do it!"
10. "Copy" under "Token" to copy your bot token
11. Save your bot token in a safe place (you will need it later)
12. Click on "OAuth2" in the left-hand menu
13. Under "Scopes", select "bot"
14. Under "Bot Permissions", select
    - View Channels
    - Send Messages
    - Create public threads
    - Use slash commands
    - Read Message History
    - Mention Everyone
15. Click on "Copy" under "OAuth2 URL" to copy the invite URL
16. Paste the invite URL into your web browser
17. Select the server you want to invite the bot to
18. Click on "Authorize"

Congratulations! Your bot has been invited to your server

### Docker

Installing the bot using Docker is the easiest way to get started. To do this, you will need to have Docker installed on
your system. If you do not have Docker installed, you can download it from
the [official Docker website](https://www.docker.com/get-started).


> [!IMPORTANT]
> Replace `YOUR_DISCORD_TOKEN` with your Discord bot token, `YOUR_CRAFTY_TOKEN` with your Crafty Controller API token
> and `YOUR_CRAFTY_SERVER_URL` with the URL of your Crafty Controller server in
> the following format: `https://your-crafty-server-IP:PORT`.

To install the bot using Docker, you will need to run the following command in your terminal:

```bash
docker run -d --name crafty-bot -e DISCORD_TOKEN=YOUR_DISCORD_TOKEN -e CRAFTY_TOKEN=YOUR_CRAFTY_TOKEN -e SERVER_URL=YOUR_CRAFTY_SERVER_URL twoplay/craftybot:latest
```

Or you can use the following `docker-compose.yml` file:

```yaml
services:
  crafty-bot:
    image: twoplay/craftybot:latest
    container_name: crafty-bot
    environment:
      - DISCORD_TOKEN=YOUR_DISCORD_TOKEN
      - CRAFTY_TOKEN=YOUR_CRAFT
      - SERVER_URL=YOUR_CRAFTY_SERVER_URL
      # Optional web dashboard
      # - WEB_ENABLED=true
      # - WEB_PASSWORD=YOUR_DASHBOARD_PASSWORD
    # ports:
    #   - "8080:8080"
    # Keeps the feature flags changed in the dashboard
    volumes:
      - crafty-bot-data:/usr/src/app/data
    restart: unless-stopped

volumes:
  crafty-bot-data:
```

### Python

If you would like to install the bot using Python, you will need to have Python 3.10 or higher installed on your system.

Clone the repository

```bash
git clone https://github.com/Two-Play/Crafty-Discord-bot.git
```

Change into the project directory

```bash
cd Crafty-Discord-bot
```

Create a virtual environment

```bash
python -m venv venv
```

Activate the virtual environment
On Linux and macOS:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

Download the required dependencies

```bash
pip install -r requirements.txt
```

To run the bot, you will need to copy the `.env.example` file to a new file called `.env` and fill in the required
fields.

| Variable                                | Required | Description                                                                    |
|-----------------------------------------|----------|--------------------------------------------------------------------------------|
| `SERVER_URL`                            | yes      | URL of your Crafty Controller, e.g. `https://your-crafty-server-IP:PORT`       |
| `DISCORD_TOKEN`                         | yes      | Your Discord bot token                                                         |
| `CRAFTY_TOKEN`                          | yes*     | Your Crafty Controller API token                                               |
| `CRAFTY_USERNAME` / `CRAFTY_PASSWORD`   | yes*     | Crafty login, used instead of `CRAFTY_TOKEN` if no token is set (not recommended) |
| `GUILD_ID`                              | no       | Discord server ID for the slash commands (without it they are synced globally) |
| `ENABLE_AUTO_STOP_SERVER`               | no       | `true` to stop running servers without players automatically (default of the `auto_stop` feature flag). Servers Crafty can't ping (unknown player count) or that are starting/updating are skipped |
| `AUTO_STOP_SLEEP_TIME`                  | no       | Interval of the auto stop check in seconds (default `1800`)                    |
| `CRAFTY_VERIFY_SSL`                     | no       | `true` to verify the TLS certificate of Crafty (default `false`, self-signed)  |
| `LOG_LEVEL`                             | no       | `DEBUG`, `INFO` (default), `WARNING` or `ERROR` (libraries never log below `INFO`) |
| `WEB_ENABLED`                           | no       | `true` to serve the web dashboard                                              |
| `WEB_HOST`                              | no       | Interface the dashboard listens on (default `127.0.0.1`, `0.0.0.0` in Docker)  |
| `WEB_PORT`                              | no       | Port of the dashboard (default `8080`)                                         |
| `WEB_PASSWORD`                          | no       | Password for the dashboard (HTTP basic auth, any user name). Strongly recommended if it is reachable from other machines |
| `FLAGS_FILE`                            | no       | File the feature flags are saved to (default `data/feature_flags.json`)        |
| `LOG_FILE`                              | no       | Also write the log to this file, e.g. `logs/bot.log` (rotated at 5 MB, 3 backups) |

\* Either `CRAFTY_TOKEN` or `CRAFTY_USERNAME` and `CRAFTY_PASSWORD` must be set.

Start the bot from the project directory

```bash
python -m core
```

#### Update

For updating the bot, you can use the following command:

```bash
# Change into the project directory and pull the latest changes
cd Crafty-Discord-bot
git pull
```

## Usage

### Slash Commands (Beta)

To use slash commands, you will need to set the `GUILD_ID` in the `.env` file. You can get the `GUILD_ID` by enabling
the `Developer Mode` in Discord and right-clicking on the server name.

To get the slash commands, enter the following command:

```bash
  >clear
  >commands
  >sync
```

Hopefully, the bot will know the commands. It is still in beta, so it may not work as expected.

The bot supports slash commands. To use the slash commands, you will need to have the `Use slash commands` permission
enabled for the bot.

```bash
  /help
```

### Command (>)

Enter the following command to get a list of available commands:

```bash
  >help
```

To get the status of the server, enter the following command:

```bash
  >status
```

To start the server, enter the following command:

```bash
  >start [server_id]
```

replace `[server_id]` with the ID of the server you want to start. You can get the server ID by entering the `>list`
command.
For example:

```bash
  >start da459ce3-6964-46b8-bb21-1c3e753b6ba9
```

To start a backup of a server (bot owner only), enter the following command:

```bash
  >backup [server_id] [backup_name]
```

Without `[backup_name]` the default backup configuration of the server is used. The backups have to be configured in
Crafty first, and the Crafty API token needs the `BACKUP` permission.

### Web dashboard

Set `WEB_ENABLED=true` to get a status page at `http://HOST:8080` (bot connection, latency, uptime and the
status, players, CPU and RAM of every server). It refreshes every 30 seconds. `/api/status` returns the same data as
JSON and `/healthz` can be used for health checks (no password needed).

#### Feature flags

The dashboard lists the feature flags: one for each server command (`list`, `stats`, `start`, `stop`, `restart`,
`backup`) and one for auto stop. A disabled command answers with "The command is currently disabled" and is hidden
from `>help`. The flags can only be changed when `WEB_PASSWORD` is set, otherwise they are read-only. Changes take
effect immediately and are saved to `FLAGS_FILE`, so they survive a restart. In Docker, mount a volume at
`/usr/src/app/data` to keep them when the container is recreated.

> [!WARNING]
> Set `WEB_PASSWORD` if the dashboard can be reached from other machines. Use a reverse proxy with HTTPS if you
> expose it to the internet, because basic auth sends the password unencrypted otherwise.

## Issues

If you encounter any issues while using the bot, please report them on the
[GitHub Issues](https://github.com/Two-Play/Crafty-Discord-bot/issues) page.

## Contributing

If you would like to contribute to the project, please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add new feature'`)
5. Push to the branch (`git push origin feature`)
6. Create a new Pull Request
7. Wait for your Pull Request to be reviewed
8. Once your Pull Request is approved, it will be merged into the main branch
9. Congratulations! You have successfully contributed to the project

Thank you for your contribution!

If you have any questions, please feel free to reach out to us

## Support the Project

If you would like to support the project, you can do so by:

- Giving the project a star on GitHub
- Sharing the project with others
- Contributing to the project
- Donating to the project

## Donations

If you would like to donate to the project, you can do so using the following methods:

| Platform                                                                                                                             | Link                                                                    | QR Code                                                                                                                                                                                           |
|--------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ![Buy Me A Coffee Badge](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FD0?logo=buymeacoffee&logoColor=000&style=for-the-badge) | [Buy Me a Coffee](https://www.buymeacoffee.com/TwoPlay)                 | ![Buy Me a Coffee QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=https://www.buymeacoffee.com/TwoPlay&qzone=1&margin=0&size=150x150&ecc=L)                 |
| ![PayPal Badge](https://img.shields.io/badge/PayPal-003087?logo=paypal&logoColor=fff&style=for-the-badge)                            | [PayPal](https://www.paypal.com/donate/?hosted_button_id=RQAUT43DDLTJG) | ![PayPal QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=https://www.paypal.com/donate/?hosted_button_id=RQAUT43DDLTJG&qzone=1&margin=0&size=150x150&ecc=L) |

### Cryptocurrency Donations

You can click on the QR code to show a larger version of the QR code. GitHub does not support displaying large images in
the README file.

| Cryptocurrency                                                                                                  | Abbreviation | <div style="min-width:150px">QR-Code</div>                                                                                                                                                                                          | Address                                                                                           |
|:----------------------------------------------------------------------------------------------------------------|:-------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------|
| ![Bitcoin Badge](https://img.shields.io/badge/Bitcoin-F7931A?logo=bitcoin&logoColor=fff&style=for-the-badge)    | BTC          | <img src="https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=bc1qk2xrz4mffeyh9dv8jm42vlejgmzft3adnweeqy&qzone=1&margin=0&size=150x150&ecc=L" style="min-width:150px" alr="Bitcoin QR-Code">               | `bc1qk2xrz4mffeyh9dv8jm42vlejgmzft3adnweeqy`                                                      |
| ![Ethereum Badge](https://img.shields.io/badge/Ethereum-3C3C3D?logo=ethereum&logoColor=fff&style=for-the-badge) | ETH          | ![Ethereum QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=0xBA615b7341C0d9aB4337dE4927B87e9E30fbE0b9&qzone=1&margin=0&size=150x150&ecc=L)                                                    | `0xBA615b7341C0d9aB4337dE4927B87e9E30fbE0b9`                                                      |
| ![Litecoin Badge](https://img.shields.io/badge/Litecoin-A6A9AA?logo=litecoin&logoColor=fff&style=for-the-badge) | LTC          | ![Litecoin QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=LNTn2u6svYMYswuwPSWTj41iXnxe4tP99i&qzone=1&margin=0&size=150x150&ecc=L)                                                            | `LNTn2u6svYMYswuwPSWTj41iXnxe4tP99i`                                                              |
| ![Monero Badge](https://img.shields.io/badge/Monero-F60?logo=monero&logoColor=fff&style=for-the-badge)          | XMR          | ![Monero QR Code](https://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&data=41hZYQV5uDzfiLCusRAxARST3hfTzGv7RNRyB92G1RZw64pvEQqwDo94zZHVxfvcmncLU1ockvJxbZBQToPqqDtBAor97sU&qzone=1&margin=0&size=150x150&ecc=L) | `41hZYQV5uDzfiLCusRAxARST3hfTzGv7RNRyB92G1RZw64pvEQqwDo94zZHVxfvcmncLU1ockvJxbZBQToPqqDtBAor97sU` |

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
