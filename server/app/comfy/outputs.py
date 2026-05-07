"""Output parsing for ComfyUI history payloads."""

from typing import Any

from app.comfy.client import ComfyUIClient
from app.schemas.comfy import OutputAsset


class ComfyUIOutputParser:
    """Extracts generated image and video assets from ComfyUI history responses."""

    _IMAGE_KEYS: set[str] = {"images"}
    _VIDEO_KEYS: set[str] = {"videos", "gifs"}

    def __init__(self, client: ComfyUIClient) -> None:
        self._client: ComfyUIClient = client

    def parse(self, history: dict[str, Any]) -> list[OutputAsset]:
        outputs: Any = history.get("outputs")
        if not isinstance(outputs, dict):
            return []

        assets: list[OutputAsset] = []
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue

            assets.extend(self._parse_media_group(node_output, self._IMAGE_KEYS, "image"))
            assets.extend(self._parse_media_group(node_output, self._VIDEO_KEYS, "video"))

        return assets

    def _parse_media_group(
        self,
        node_output: dict[str, Any],
        media_keys: set[str],
        media_type: str,
    ) -> list[OutputAsset]:
        assets: list[OutputAsset] = []
        for media_key in media_keys:
            media_items: Any = node_output.get(media_key)
            if not isinstance(media_items, list):
                continue

            for media_item in media_items:
                if not isinstance(media_item, dict):
                    continue
                asset: OutputAsset | None = self._parse_asset(media_item, media_type)
                if asset is not None:
                    assets.append(asset)
        return assets

    def _parse_asset(self, media_item: dict[str, Any], media_type: str) -> OutputAsset | None:
        filename: Any = media_item.get("filename")
        if not isinstance(filename, str) or not filename:
            return None

        subfolder: Any = media_item.get("subfolder", "")
        output_type: Any = media_item.get("type", "output")
        if not isinstance(subfolder, str) or not isinstance(output_type, str):
            return None

        return OutputAsset(
            filename=filename,
            subfolder=subfolder,
            type=output_type,
            media_type=media_type,
            url=self._client.build_output_url(filename, subfolder, output_type),
        )
