"""Async REST client for ComfyUI public API endpoints."""

from typing import Any
from urllib.parse import quote

import httpx

from app.comfy.exceptions import ComfyUIConnectionError, ComfyUIResponseError
from app.core.config import Settings


class ComfyUIClient:
    """Communicates with an independently running ComfyUI instance through HTTP."""

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=settings.comfyui_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.comfyui_request_timeout_seconds),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def ping(self) -> bool:
        try:
            response: httpx.Response = await self._client.get("/system_stats")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ComfyUIConnectionError(str(exc)) from exc
        return True

    async def queue_prompt(self, workflow: dict[str, Any], client_id: str) -> str:
        payload: dict[str, Any] = {
            "prompt": workflow,
            "client_id": client_id,
        }
        response_data: dict[str, Any] = await self._post_json("/prompt", payload)
        prompt_id: Any = response_data.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyUIResponseError("ComfyUI response did not include a prompt_id.")
        return prompt_id

    async def get_history(self, prompt_id: str) -> dict[str, Any]:
        response_data: dict[str, Any] = await self._get_json(f"/history/{prompt_id}")
        prompt_history: Any = response_data.get(prompt_id)
        if not isinstance(prompt_history, dict):
            raise ComfyUIResponseError("ComfyUI history response did not include the requested prompt.")
        return prompt_history

    async def get_queue(self) -> dict[str, Any]:
        return await self._get_json("/queue")

    async def interrupt(self) -> None:
        await self._post_json("/interrupt", {})

    def build_output_url(self, filename: str, subfolder: str, output_type: str) -> str:
        path_parts: list[str] = [self._settings.output_url_prefix.strip("/")]
        if subfolder:
            path_parts.extend(part for part in subfolder.split("/") if part)
        path_parts.append(filename)
        encoded_path: str = "/".join(quote(part) for part in path_parts)
        return f"/{encoded_path}"

    async def _get_json(self, path: str) -> dict[str, Any]:
        try:
            response: httpx.Response = await self._client.get(path)
            response.raise_for_status()
            response_data: Any = response.json()
        except httpx.HTTPError as exc:
            raise ComfyUIConnectionError(str(exc)) from exc
        except ValueError as exc:
            raise ComfyUIResponseError("ComfyUI returned invalid JSON.") from exc

        if not isinstance(response_data, dict):
            raise ComfyUIResponseError("ComfyUI returned an unexpected response payload.")
        return response_data

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response: httpx.Response = await self._client.post(path, json=payload)
            response.raise_for_status()
            response_data: Any = response.json()
        except httpx.HTTPStatusError as exc:
            raise ComfyUIResponseError(exc.response.text) from exc
        except httpx.HTTPError as exc:
            raise ComfyUIConnectionError(str(exc)) from exc
        except ValueError as exc:
            raise ComfyUIResponseError("ComfyUI returned invalid JSON.") from exc

        if not isinstance(response_data, dict):
            raise ComfyUIResponseError("ComfyUI returned an unexpected response payload.")
        return response_data
