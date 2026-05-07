"""ComfyUI history output parser tests."""

from app.comfy.client import ComfyUIClient
from app.comfy.outputs import ComfyUIOutputParser
from app.core.config import Settings
from app.schemas.comfy import OutputAsset


def test_output_parser_extracts_images_and_videos() -> None:
    client: ComfyUIClient = ComfyUIClient(Settings(comfyui_base_url="http://comfyui:8188"))
    parser: ComfyUIOutputParser = ComfyUIOutputParser(client)
    history: dict[str, object] = {
        "outputs": {
            "9": {
                "images": [
                    {
                        "filename": "image.png",
                        "subfolder": "",
                        "type": "output",
                    },
                ],
            },
            "10": {
                "videos": [
                    {
                        "filename": "video.mp4",
                        "subfolder": "clips",
                        "type": "output",
                    },
                ],
            },
        },
    }

    assets: list[OutputAsset] = parser.parse(history)

    assert len(assets) == 2
    assert assets[0].filename == "image.png"
    assert assets[0].media_type == "image"
    assert assets[0].url == "/outputs/image.png"
    assert assets[1].filename == "video.mp4"
    assert assets[1].media_type == "video"
    assert assets[1].url == "/outputs/clips/video.mp4"
