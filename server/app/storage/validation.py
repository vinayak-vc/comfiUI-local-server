"""Upload validation and media classification."""

from pathlib import Path

from app.core.config import Settings
from app.schemas.storage import AssetMediaType
from app.storage.exceptions import StorageValidationError


class UploadValidator:
    """Validates uploaded file names, sizes, and media types."""

    _IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    _VIDEO_EXTENSIONS: set[str] = {".mp4", ".webm", ".mov"}

    def __init__(self, settings: Settings) -> None:
        self._max_upload_size_bytes: int = settings.max_upload_size_bytes
        self._allowed_extensions: set[str] = {extension.lower() for extension in settings.allowed_upload_extensions}

    def validate_filename(self, filename: str | None) -> str:
        if filename is None or not filename.strip():
            raise StorageValidationError("Upload filename is required.")

        original_filename: str = Path(filename).name
        extension: str = Path(original_filename).suffix.lower()
        if extension not in self._allowed_extensions:
            raise StorageValidationError("Upload file extension is not allowed.")
        return original_filename

    def validate_size(self, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise StorageValidationError("Upload file is empty.")
        if size_bytes > self._max_upload_size_bytes:
            raise StorageValidationError("Upload file exceeds configured size limit.")

    def classify(self, filename: str, content_type: str | None) -> AssetMediaType:
        extension: str = Path(filename).suffix.lower()
        if extension in self._IMAGE_EXTENSIONS:
            if content_type is not None and not content_type.startswith("image/"):
                raise StorageValidationError("Upload content type does not match image extension.")
            return AssetMediaType.IMAGE

        if extension in self._VIDEO_EXTENSIONS:
            if content_type is not None and not content_type.startswith("video/"):
                raise StorageValidationError("Upload content type does not match video extension.")
            return AssetMediaType.VIDEO

        return AssetMediaType.OTHER
