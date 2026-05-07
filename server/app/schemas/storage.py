"""Storage schemas for uploaded and generated assets."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AssetKind(StrEnum):
    UPLOAD = "upload"
    OUTPUT = "output"


class AssetMediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    OTHER = "other"


class AssetResponse(BaseModel):
    id: str
    kind: AssetKind
    media_type: AssetMediaType
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    relative_path: str
    url: str
    created_at: datetime


class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    total: int


class OutputRegistrationRequest(BaseModel):
    relative_path: str
    content_type: str | None = None
    original_filename: str | None = None


class CleanupResult(BaseModel):
    deleted_assets: int = Field(ge=0)
    deleted_files: int = Field(ge=0)
