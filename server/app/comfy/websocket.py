"""WebSocket progress listener for ComfyUI execution events."""

import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode

import websockets
from websockets.asyncio.client import ClientConnection

from app.comfy.exceptions import ComfyUIConnectionError, ComfyUIResponseError
from app.core.config import Settings


class ComfyUIWebSocketListener:
    """Streams progress messages from ComfyUI for a queued prompt."""

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings

    async def listen(self, client_id: str, prompt_id: str) -> AsyncIterator[dict[str, Any]]:
        websocket_url: str = self._build_websocket_url(client_id)
        try:
            async with websockets.connect(
                websocket_url,
                open_timeout=self._settings.comfyui_request_timeout_seconds,
            ) as websocket:
                async for raw_message in websocket:
                    message: dict[str, Any] | None = self._parse_message(raw_message)
                    if message is None:
                        continue

                    if self._message_matches_prompt(message, prompt_id):
                        yield message

                    if self._is_completion_message(message, prompt_id):
                        return
        except OSError as exc:
            raise ComfyUIConnectionError(str(exc)) from exc
        except websockets.WebSocketException as exc:
            raise ComfyUIConnectionError(str(exc)) from exc

    def _build_websocket_url(self, client_id: str) -> str:
        query_string: str = urlencode({"clientId": client_id})
        return f"{self._settings.comfyui_ws_url}?{query_string}"

    def _parse_message(self, raw_message: str | bytes) -> dict[str, Any] | None:
        if isinstance(raw_message, bytes):
            return {
                "type": "preview_image",
                "data": {
                    "bytes": raw_message,
                },
            }

        try:
            parsed_message: Any = json.loads(raw_message)
        except json.JSONDecodeError as exc:
            raise ComfyUIResponseError("ComfyUI websocket returned invalid JSON.") from exc

        if not isinstance(parsed_message, dict):
            return None
        return parsed_message

    def _message_matches_prompt(self, message: dict[str, Any], prompt_id: str) -> bool:
        data: Any = message.get("data")
        if not isinstance(data, dict):
            return False

        message_prompt_id: Any = data.get("prompt_id")
        return message_prompt_id is None or message_prompt_id == prompt_id

    def _is_completion_message(self, message: dict[str, Any], prompt_id: str) -> bool:
        if message.get("type") != "executing":
            return False

        data: Any = message.get("data")
        if not isinstance(data, dict):
            return False

        return data.get("prompt_id") == prompt_id and data.get("node") is None
