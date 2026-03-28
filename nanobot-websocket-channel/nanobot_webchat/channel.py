"""WebChat channel — WebSocket server for web clients."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.asyncio.server import Server as WebSocketServer
from websockets.asyncio.server import ServerConnection
from loguru import logger
from pydantic import Field

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import Base

from .structured import parse_outbound


class WebChatConfig(Base):
    """WebChat channel configuration."""

    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8765
    allow_from: list[str] = Field(default_factory=lambda: ["*"])


class WebChatChannel(BaseChannel):
    """WebSocket-based web chat channel.

    Each WebSocket connection is treated as an independent chat session.
    Protocol (JSON):
        Client -> Server:  {"content": "hello"}
        Server -> Client:  {"content": "response text"}

    Access control:
        Set NANOBOT_ACCESS_KEY env var to require authentication.
        Clients pass the key via query parameter: ws://host:port?access_key=SECRET
        Connections without a valid key are rejected. LMS-aware clients may
        also provide ?api_key=...; when present it is forwarded to the agent
        as a prompt prefix for backwards compatibility.
    """

    name = "webchat"
    display_name = "WebChat"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return WebChatConfig().model_dump(by_alias=True)

    def __init__(self, config: Any, bus: MessageBus):
        if isinstance(config, dict):
            config = WebChatConfig.model_validate(config)
        super().__init__(config, bus)
        self.config: WebChatConfig = config
        self._connections: dict[str, ServerConnection] = {}
        self._server: WebSocketServer | None = None
        self._access_key: str = os.environ.get("NANOBOT_ACCESS_KEY", "")

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        if not self._access_key:
            raise RuntimeError("WebChat: NANOBOT_ACCESS_KEY must be set")
        logger.info("WebChat starting on {}:{}", self.config.host, self.config.port)
        self._server = await websockets.serve(
            self._handle_ws,
            self.config.host,
            self.config.port,
        )
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._connections.clear()

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message back to the client via its WebSocket."""
        ws = self._connections.get(msg.chat_id)
        if ws is None:
            logger.warning("WebChat: no connection for chat_id={}", msg.chat_id)
            return
        try:
            result = parse_outbound(msg.content)
            await ws.send(result.model_dump_json())
        except websockets.ConnectionClosed:
            logger.info("WebChat: connection closed for chat_id={}", msg.chat_id)
            self._connections.pop(msg.chat_id, None)

    async def _handle_ws(self, ws: ServerConnection) -> None:
        """Handle a single WebSocket connection lifecycle."""
        # Validate access key
        path: str = ws.request.path if ws.request is not None else ""
        qs = parse_qs(urlparse(path).query)
        client_key: str = qs.get("access_key", [""])[0]
        api_key: str = qs.get("api_key", [""])[0].strip()

        if self._access_key and client_key != self._access_key:
            logger.warning("WebChat: rejected connection — invalid access key")
            await ws.close(4001, "Invalid access key")
            return

        chat_id = str(uuid.uuid4())
        self._connections[chat_id] = ws
        sender_id = chat_id

        logger.info("WebChat: new connection chat_id={}", chat_id)

        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                    content = data.get("content", "").strip()
                except (json.JSONDecodeError, AttributeError):
                    content = str(raw).strip()

                if not content:
                    continue

                if api_key:
                    # Preserve the legacy per-user LMS credential flow used by
                    # the Telegram client without reusing it as deployment auth.
                    content = f"[LMS_API_KEY={api_key}] {content}"

                await self._handle_message(
                    sender_id=sender_id,
                    chat_id=chat_id,
                    content=content,
                )
        except websockets.ConnectionClosed:
            pass
        finally:
            self._connections.pop(chat_id, None)
            logger.info("WebChat: disconnected chat_id={}", chat_id)
