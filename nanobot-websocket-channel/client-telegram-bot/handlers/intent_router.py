"""Route free-text messages to the nanobot AI agent via WebSocket."""

from typing import Any

from services.nanobot_client import NanobotClient


async def route_intent(
    user_message: str, nanobot_client: NanobotClient, api_key: str = ""
) -> dict[str, Any]:
    """Forward a natural language message to the nanobot agent.

    Returns a structured message dict (see nanobot/plan.md protocol spec).
    """
    try:
        return await nanobot_client.ask(user_message, api_key=api_key)
    except Exception as e:
        return {
            "type": "text",
            "content": f"⚠️ Could not reach the AI agent: {e}",
            "format": "plain",
        }
