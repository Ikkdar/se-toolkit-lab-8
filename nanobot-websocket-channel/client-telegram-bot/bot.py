#!/usr/bin/env python3
"""SE Toolkit Bot - Telegram bot for LMS interaction."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.filters import Command

from settings import settings
from handlers.commands import MessageHandler, SessionHandlers, cmd_help, cmd_start
from services.nanobot_client import NanobotClient


def main() -> None:
    user_keys: dict[int, str] = {}
    nanobot_client = NanobotClient(
        ws_url=settings.nanobot_ws_url,
        access_key=settings.nanobot_access_key,
    )
    session = SessionHandlers(user_keys)
    messages = MessageHandler(nanobot_client, user_keys)

    dp = Dispatcher()
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(session.cmd_login, Command("login"))
    dp.message.register(session.cmd_logout, Command("logout"))
    dp.message.register(messages.handle_message)
    dp.callback_query.register(messages.handle_callback)

    print("Starting bot...")
    dp.run_polling(Bot(token=settings.bot_token))


if __name__ == "__main__":
    main()
