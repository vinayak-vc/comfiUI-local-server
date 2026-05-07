"""Output file proxy endpoint tests."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.output_proxy import router
from app.core.config import Settings


class FakeComfyClient:
    async def get_output_file(
        self,
        filename: str,
        subfolder: str,
        output_type: str,
    ) -> tuple[bytes, str]:
        return f"{output_type}:{subfolder}:{filename}".encode("utf-8"), "image/png"


def test_output_proxy_serves_comfyui_file_when_not_local(tmp_path: Path) -> None:
    app: FastAPI = _app(tmp_path)
    client: TestClient = TestClient(app, base_url="http://192.168.1.196:8000")

    response = client.get("/outputs/ComfyUI_00009_.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"output::ComfyUI_00009_.png"


def test_output_proxy_serves_subfolder_from_comfyui(tmp_path: Path) -> None:
    app: FastAPI = _app(tmp_path)
    client: TestClient = TestClient(app)

    response = client.get("/outputs/clips/video.mp4?type=output")

    assert response.status_code == 200
    assert response.content == b"output:clips:video.mp4"


def test_output_proxy_rejects_path_traversal(tmp_path: Path) -> None:
    app: FastAPI = _app(tmp_path)
    client: TestClient = TestClient(app)

    response = client.get("/outputs/../secret.txt")

    assert response.status_code == 404


def _app(outputs_path: Path) -> FastAPI:
    app = FastAPI()
    app.state.settings = Settings(outputs_path=outputs_path)
    app.state.comfy_client = FakeComfyClient()
    app.include_router(router)
    return app
