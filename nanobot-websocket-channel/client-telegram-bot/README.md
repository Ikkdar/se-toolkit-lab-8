# SE Toolkit Bot

Telegram bot for interacting with an LMS-aware Nanobot deployment.

## Quick Start

### 1. Setup environment

Set these environment variables before starting the bot:

- `BOT_TOKEN` — Telegram bot token from @BotFather
- `NANOBOT_WS_URL` — WebSocket endpoint exposed by the Nanobot channel
- `NANOBOT_ACCESS_KEY` — deployment access key for the Nanobot WebSocket channel

If your agent setup expects per-user LMS credentials, users can provide them at runtime with `/login <api_key>`. The bot will send that key separately from the deployment access key.

### 2. Test mode

Test commands without Telegram:

```bash
uv run bot.py --test "/start"
uv run bot.py --test "/help"
uv run bot.py --test "/health"
uv run bot.py --test "/labs"
uv run bot.py --test "/scores lab-04"
```

### 3. Run the bot

```bash
uv run bot.py
```

## Available Commands

| Command         | Description               |
| --------------- | ------------------------- |
| `/start`        | Welcome message           |
| `/help`         | List all commands         |
| `/health`       | Check backend status      |
| `/labs`         | List available labs       |
| `/scores <lab>` | View pass rates for a lab |

## Natural Language Queries

You can also ask questions in plain language:

- "What labs are available?"
- "Show me the scores for lab-04"
- "Is the backend working?"
- "Who are the top learners in lab-01?"

## Docker Deployment

Add to `.env.docker.secret`:

```bash
BOT_TOKEN=your-telegram-bot-token
NANOBOT_WS_URL=ws://host.docker.internal:8765
NANOBOT_ACCESS_KEY=your-private-access-key
```

Then run:

```bash
docker compose --env-file .env.docker.secret up -d bot
```

## Architecture

- **Handlers** (`handlers/`) — Command logic, testable without Telegram
- **Services** (`services/`) — WebSocket client for the Nanobot channel
- **Entry point** (`bot.py`) — `--test` mode and Telegram startup
