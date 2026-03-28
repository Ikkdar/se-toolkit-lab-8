"""WebSocket client for the nanobot AI agent gateway."""

import json
from typing import Any
from urllib.parse import urlencode

import websockets


class NanobotClient:
    """Forwards messages to the nanobot agent over WebSocket."""

    def __init__(self, ws_url: str, access_key: str):
        self.ws_url = ws_url
        self.access_key = access_key

    async def ask(self, message: str, api_key: str = "") -> dict[str, Any]:
        """Send a message and return the agent's structured response.

        The deployment access key is always sent so the channel accepts the
        connection. If *api_key* is provided it is forwarded as an extra query
        parameter for setups that still use per-user LMS credentials.

        Returns a dict with at least ``type`` and ``content`` fields.
        """
        url = self.ws_url
        query: dict[str, str] = {"access_key": self.access_key}
        if api_key:
            query["api_key"] = api_key
        if query:
            url = f"{self.ws_url}?{urlencode(query)}"
        async with websockets.connect(url, close_timeout=5) as ws:
            await ws.send(json.dumps({"content": message}))
            raw = await ws.recv()
            data: dict[str, Any] = json.loads(raw)
            # Backwards compat: if no type field, wrap as text
            if "type" not in data:
                return {
                    "type": "text",
                    "content": data.get("content", ""),
                    "format": "markdown",
                }
            return data
