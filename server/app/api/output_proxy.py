"""Client-facing output file serving."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.comfy.client import ComfyUIClient
from app.comfy.exceptions import ComfyUIError
from app.core.config import Settings

router: APIRouter = APIRouter()


@router.get("/outputs/{output_path:path}")
async def get_output_file(
    output_path: str,
    request: Request,
    output_type: str = Query(default="output", alias="type"),
) -> Response:
    """Serve generated output files from local storage or the upstream ComfyUI instance."""

    path_parts: list[str] = _safe_output_path_parts(output_path)
    filename: str = path_parts[-1]
    subfolder: str = "/".join(path_parts[:-1])

    settings: Settings = request.app.state.settings
    local_path: Path = _resolve_local_output_path(settings.outputs_path, path_parts)
    if local_path.exists() and local_path.is_file():
        return FileResponse(local_path)

    comfy_client: ComfyUIClient = request.app.state.comfy_client
    try:
        content, media_type = await comfy_client.get_output_file(filename, subfolder, output_type)
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Output file not found.",
        ) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def _safe_output_path_parts(output_path: str) -> list[str]:
    path_parts: list[str] = [part for part in Path(output_path).parts if part not in {"", "."}]
    if not path_parts or any(part == ".." for part in path_parts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Output path is not allowed.",
        )
    return path_parts


def _resolve_local_output_path(outputs_path: Path, path_parts: list[str]) -> Path:
    output_root: Path = outputs_path.resolve()
    local_path: Path = output_root.joinpath(*path_parts).resolve()
    if output_root not in local_path.parents and local_path != output_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Output path is not allowed.",
        )
    return local_path
