"""Asset storage routes."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.dependencies import get_database_session, get_settings, require_principal
from app.core.config import Settings
from app.schemas.storage import AssetListResponse, AssetResponse, CleanupResult, OutputRegistrationRequest
from app.storage.exceptions import AssetNotFoundError, StorageValidationError
from app.storage.service import StorageService
from sqlalchemy.ext.asyncio import AsyncSession

router: APIRouter = APIRouter(dependencies=[Depends(require_principal)])


def get_route_storage_service(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_database_session),
) -> StorageService:
    return StorageService(settings, session)


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: UploadFile = File(...),
    storage_service: StorageService = Depends(get_route_storage_service),
) -> AssetResponse:
    try:
        return await storage_service.store_upload(file)
    except StorageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    storage_service: StorageService = Depends(get_route_storage_service),
) -> AssetListResponse:
    return await storage_service.list_assets(limit=limit, offset=offset)


@router.post("/outputs/register", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def register_output_asset(
    request: OutputRegistrationRequest,
    storage_service: StorageService = Depends(get_route_storage_service),
) -> AssetResponse:
    try:
        return await storage_service.register_output(
            relative_path=request.relative_path,
            content_type=request.content_type,
            original_filename=request.original_filename,
        )
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except StorageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    storage_service: StorageService = Depends(get_route_storage_service),
) -> AssetResponse:
    try:
        return await storage_service.get_asset(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: str,
    storage_service: StorageService = Depends(get_route_storage_service),
) -> FileResponse:
    try:
        asset: AssetResponse = await storage_service.get_asset(asset_id)
        asset_path = await storage_service.get_asset_path(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return FileResponse(
        path=asset_path,
        media_type=asset.content_type,
        filename=asset.original_filename,
    )


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    storage_service: StorageService = Depends(get_route_storage_service),
) -> None:
    try:
        await storage_service.delete_asset(asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/cleanup", response_model=CleanupResult)
async def cleanup_expired_uploads(
    storage_service: StorageService = Depends(get_route_storage_service),
) -> CleanupResult:
    return await storage_service.cleanup_expired_uploads()
