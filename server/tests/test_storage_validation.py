"""Storage validation and path safety tests."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.schemas.storage import AssetMediaType
from app.storage.backend import LocalStorageBackend
from app.storage.exceptions import StorageValidationError
from app.storage.validation import UploadValidator


def test_upload_validator_accepts_image_upload() -> None:
    validator: UploadValidator = UploadValidator(Settings())

    filename: str = validator.validate_filename("portrait.png")
    media_type: AssetMediaType = validator.classify(filename, "image/png")

    assert filename == "portrait.png"
    assert media_type == AssetMediaType.IMAGE


def test_upload_validator_rejects_disallowed_extension() -> None:
    validator: UploadValidator = UploadValidator(Settings())

    with pytest.raises(StorageValidationError):
        validator.validate_filename("payload.exe")


def test_local_storage_backend_rejects_path_traversal(tmp_path: Path) -> None:
    backend: LocalStorageBackend = LocalStorageBackend(tmp_path, "/uploads")

    with pytest.raises(StorageValidationError):
        backend.resolve("../escape.png")
