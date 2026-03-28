"""Command and message handlers for the Telegram bot."""

from __future__ import annotations

from aiogram import types

from handlers.intent_router import route_intent
from handlers.renderer import render
from services.nanobot_client import NanobotClient


HELP_TEXT = (
    "📚 Available commands:\n\n"
    "• /start - Welcome message\n"
    "• /help - Show this help message\n"
    "• /login <api_key> - Set your LMS API key\n"
    "• /logout - Remove your LMS API key\n\n"
    "You can also ask questions in plain language, like:\n"
    "• 'Is the backend healthy?'\n"
    "• 'What labs are available?'\n"
    "• 'Show me the scores for lab-04'"
)

WELCOME_TEXT = (
    "👋 Welcome to SE Toolkit Bot!\n\n"
    "I'm your LMS assistant. To get started, set your API key:\n"
    "  /login <your-api-key>\n\n"
    "Then ask me anything in plain language,\n"
    "or type /help to see available commands."
)


async def cmd_start(message: types.Message) -> None:
    await message.answer(WELCOME_TEXT)


async def cmd_help(message: types.Message) -> None:
    await message.answer(HELP_TEXT)


class SessionHandlers:
    def __init__(self, user_keys: dict[int, str]) -> None:
        self.user_keys = user_keys

    async def cmd_login(self, message: types.Message) -> None:
        if not message.from_user:
            return
        args = message.text.split()[1:] if message.text else []
        if not args:
            await message.answer("Usage: /login <api_key>")
            return
        self.user_keys[message.from_user.id] = args[0]
        await message.answer("✅ API key saved. You can now ask questions.")

    async def cmd_logout(self, message: types.Message) -> None:
        if not message.from_user:
            return
        self.user_keys.pop(message.from_user.id, None)
        await message.answer("🔓 API key removed.")


class MessageHandler:
    def __init__(
        self, nanobot_client: NanobotClient, user_keys: dict[int, str]
    ) -> None:
        self.nanobot_client = nanobot_client
        self.user_keys = user_keys

    async def handle_message(self, message: types.Message) -> None:
        if not message.from_user or not message.text:
            return
        api_key = self.user_keys.get(message.from_user.id, "")
        if not api_key:
            await message.answer("🔑 Please set your API key first: /login <api_key>")
            return
        response = await route_intent(
            message.text, self.nanobot_client, api_key=api_key
        )
        await render(message, response)

    async def handle_callback(self, callback: types.CallbackQuery) -> None:
        await callback.answer()
        if not callback.from_user or not callback.data:
            return
        if not isinstance(callback.message, types.Message):
            return
        api_key = self.user_keys.get(callback.from_user.id, "")
        if not api_key:
            await callback.message.answer(
                "🔑 Please set your API key first: /login <api_key>"
            )
            return
        response = await route_intent(
            callback.data, self.nanobot_client, api_key=api_key
        )
        await render(callback.message, response)
