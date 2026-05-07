"""Asset storage business service."""

import hashlib
import mimetypes
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.asset import Asset
from app.schemas.storage import AssetKind, AssetListResponse, AssetMediaType, AssetResponse, CleanupResult
from app.storage.backend import LocalStorageBackend
from app.storage.exceptions import AssetNotFoundError
from app.storage.validation import UploadValidator


class StorageService:
    """Coordinates upload storage, metadata persistence, serving, and cleanup."""

    _CHUNK_SIZE: int = 1024 * 1024

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings: Settings = settings
        self._session: AsyncSession = session
        self._validator: UploadValidator = UploadValidator(settings)
        self._upload_backend: LocalStorageBackend = LocalStorageBackend(
            settings.uploads_path,
            settings.upload_url_prefix,
        )
        self._output_backend: LocalStorageBackend = LocalStorageBackend(
            settings.outputs_path,
            settings.output_url_prefix,
        )

    async def store_upload(self, upload_file: UploadFile) -> AssetResponse:
        original_filename: str = self._validator.validate_filename(upload_file.filename)
        content_type: str = upload_file.content_type or "application/octet-stream"
        media_type: AssetMediaType = self._validator.classify(original_filename, upload_file.content_type)
        extension: str = Path(original_filename).suffix.lower()
        stored_filename: str = f"{uuid4()}{extension}"
        relative_path: str = self._build_relative_path(stored_filename)
        checksum = hashlib.sha256()
        size_bytes: int = 0

        try:
            while True:
                chunk: bytes = await upload_file.read(self._CHUNK_SIZE)
                if not chunk:
                    break

                size_bytes += len(chunk)
                self._validator.validate_size(size_bytes)
                checksum.update(chunk)
                await self._upload_backend.write_chunk(relative_path, chunk)

            self._validator.validate_size(size_bytes)
            asset: Asset = Asset.create_upload(
                media_type=media_type,
                original_filename=original_filename,
                stored_filename=stored_filename,
                content_type=content_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum.hexdigest(),
                relative_path=relative_path,
            )
            self._session.add(asset)
            await self._session.commit()
            await self._session.refresh(asset)
            return self._to_response(asset)
        except Exception:
            await self._session.rollback()
            await self._upload_backend.delete(relative_path)
            raise
        finally:
            await upload_file.close()

    async def register_output(
        self,
        relative_path: str,
        content_type: str | None,
        original_filename: str | None,
    ) -> AssetResponse:
        output_path: Path = self._output_backend.require_file(relative_path)
        existing_result = await self._session.execute(select(Asset).where(Asset.relative_path == relative_path))
        existing_asset: Asset | None = existing_result.scalar_one_or_none()
        if existing_asset is not None:
            return self._to_response(existing_asset)

        stored_filename: str = output_path.name
        resolved_content_type: str = content_type or self._guess_content_type(output_path)
        media_type: AssetMediaType = self._media_type_from_content_type(resolved_content_type)
        checksum_sha256: str = await self._checksum_file(output_path)
        size_bytes: int = output_path.stat().st_size
        asset: Asset = Asset.create_output(
            media_type=media_type,
            original_filename=original_filename or stored_filename,
            stored_filename=stored_filename,
            content_type=resolved_content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            relative_path=relative_path,
        )

        self._session.add(asset)
        await self._session.commit()
        await self._session.refresh(asset)
        return self._to_response(asset)

    async def list_assets(self, limit: int, offset: int) -> AssetListResponse:
        total_result = await self._session.execute(select(func.count()).select_from(Asset))
        total: int = int(total_result.scalar_one())
        query: Select[tuple[Asset]] = select(Asset).order_by(Asset.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(query)
        assets: list[AssetResponse] = [self._to_response(asset) for asset in result.scalars().all()]
        return AssetListResponse(assets=assets, total=total)

    async def get_asset(self, asset_id: str) -> AssetResponse:
        asset: Asset = await self._require_asset(asset_id)
        return self._to_response(asset)

    async def get_asset_path(self, asset_id: str) -> Path:
        asset: Asset = await self._require_asset(asset_id)
        return self._backend_for(asset).require_file(asset.relative_path)

    async def delete_asset(self, asset_id: str) -> None:
        asset: Asset = await self._require_asset(asset_id)
        await self._backend_for(asset).delete(asset.relative_path)
        await self._session.delete(asset)
        await self._session.commit()

    async def cleanup_expired_uploads(self) -> CleanupResult:
        cutoff: datetime = datetime.now(UTC) - timedelta(days=self._settings.storage_cleanup_after_days)
        result = await self._session.execute(
            select(Asset).where(
                Asset.created_at < cutoff,
                Asset.kind == AssetKind.UPLOAD.value,
            )
        )
        assets: list[Asset] = list(result.scalars().all())
        deleted_files: int = 0
        deleted_assets: int = 0

        for asset in assets:
            if await self._upload_backend.delete(asset.relative_path):
                deleted_files += 1
            await self._session.delete(asset)
            deleted_assets += 1

        await self._session.commit()
        return CleanupResult(deleted_assets=deleted_assets, deleted_files=deleted_files)

    async def _require_asset(self, asset_id: str) -> Asset:
        asset: Asset | None = await self._session.get(Asset, asset_id)
        if asset is None:
            raise AssetNotFoundError("Asset not found.")
        return asset

    def _build_relative_path(self, stored_filename: str) -> str:
        current_date: datetime = datetime.now(UTC)
        return f"{current_date:%Y/%m/%d}/{stored_filename}"

    def _to_response(self, asset: Asset) -> AssetResponse:
        backend: LocalStorageBackend = self._backend_for(asset)
        return AssetResponse(
            id=asset.id,
            kind=asset.kind,
            media_type=asset.media_type,
            original_filename=asset.original_filename,
            stored_filename=asset.stored_filename,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
            checksum_sha256=asset.checksum_sha256,
            relative_path=asset.relative_path,
            url=backend.url_for(asset.relative_path),
            created_at=asset.created_at,
        )

    def _backend_for(self, asset: Asset) -> LocalStorageBackend:
        if asset.kind == AssetKind.OUTPUT.value:
            return self._output_backend
        return self._upload_backend

    async def _checksum_file(self, path: Path) -> str:
        checksum = hashlib.sha256()
        async with aiofiles.open(path, "rb") as file:
            while True:
                chunk: bytes = await file.read(self._CHUNK_SIZE)
                if not chunk:
                    break
                checksum.update(chunk)
        return checksum.hexdigest()

    def _guess_content_type(self, path: Path) -> str:
        content_type: str | None
        content_type, _ = mimetypes.guess_type(path.name)
        return content_type or "application/octet-stream"

    def _media_type_from_content_type(self, content_type: str) -> AssetMediaType:
        if content_type.startswith("image/"):
            return AssetMediaType.IMAGE
        if content_type.startswith("video/"):
            return AssetMediaType.VIDEO
        return AssetMediaType.OTHER
