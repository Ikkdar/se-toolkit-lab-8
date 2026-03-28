"""Render structured nanobot messages as Telegram responses."""

from typing import Any

from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TELEGRAM_MAX_LENGTH = 4096


def _split_text(text: str, limit: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split text into chunks that fit Telegram's message length limit."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to split at last newline within limit
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks


async def render(message: types.Message, response: dict[str, Any]) -> None:
    """Render a structured nanobot response to a Telegram chat."""
    msg_type = response.get("type", "text")

    if msg_type == "text":
        await _render_text(message, response)
    elif msg_type == "choice":
        await _render_choice(message, response)
    elif msg_type == "confirm":
        await _render_confirm(message, response)
    elif msg_type == "composite":
        for part in response.get("parts", []):
            await render(message, part)
    else:
        # Unknown type — render content as plain text
        await message.answer(response.get("content", str(response)))


async def _render_text(message: types.Message, response: dict[str, Any]) -> None:
    content = response.get("content", "")
    for chunk in _split_text(content):
        await message.answer(chunk)


async def _render_choice(message: types.Message, response: dict[str, Any]) -> None:
    content = response.get("content", "Choose an option:")
    options: list[dict[str, str]] = response.get("options", [])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt["label"], callback_data=opt["value"])]
            for opt in options
        ]
    )
    await message.answer(content, reply_markup=keyboard)


async def _render_confirm(message: types.Message, response: dict[str, Any]) -> None:
    content = response.get("content", "Are you sure?")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes", callback_data="yes"),
                InlineKeyboardButton(text="No", callback_data="no"),
            ]
        ]
    )
    await message.answer(content, reply_markup=keyboard)
