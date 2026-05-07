"""Local filesystem storage backend with future S3-compatible boundary."""

from pathlib import Path
from typing import Protocol

import aiofiles

from app.storage.exceptions import AssetNotFoundError, StorageValidationError


class StorageBackend(Protocol):
    async def write_chunk(self, relative_path: str, data: bytes) -> None:
        """Append a chunk to a stored object."""

    async def delete(self, relative_path: str) -> bool:
        """Delete a stored object."""

    def resolve(self, relative_path: str) -> Path:
        """Resolve a stored object path."""

    def url_for(self, relative_path: str) -> str:
        """Build a public URL for a stored object."""


class LocalStorageBackend:
    """Stores assets under a configured local root using safe relative paths."""

    def __init__(self, root_path: Path, url_prefix: str) -> None:
        self._root_path: Path = root_path.resolve()
        self._url_prefix: str = url_prefix.rstrip("/")
        self._root_path.mkdir(parents=True, exist_ok=True)

    async def write_chunk(self, relative_path: str, data: bytes) -> None:
        target_path: Path = self.resolve(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target_path, "ab") as file:
            await file.write(data)

    async def delete(self, relative_path: str) -> bool:
        target_path: Path = self.resolve(relative_path)
        if not target_path.exists():
            return False

        target_path.unlink()
        return True

    def resolve(self, relative_path: str) -> Path:
        clean_path: Path = Path(relative_path)
        if clean_path.is_absolute() or ".." in clean_path.parts:
            raise StorageValidationError("Invalid storage path.")

        target_path: Path = (self._root_path / clean_path).resolve()
        if self._root_path not in target_path.parents and target_path != self._root_path:
            raise StorageValidationError("Storage path escapes configured root.")
        return target_path

    def url_for(self, relative_path: str) -> str:
        safe_path: str = "/".join(Path(relative_path).parts)
        return f"{self._url_prefix}/{safe_path}"

    def require_file(self, relative_path: str) -> Path:
        target_path: Path = self.resolve(relative_path)
        if not target_path.exists() or not target_path.is_file():
            raise AssetNotFoundError("Asset file not found.")
        return target_path
