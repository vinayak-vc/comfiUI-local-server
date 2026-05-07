"""Asset metadata ORM model."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.schemas.storage import AssetKind, AssetMediaType


class Asset(Base):
    """Metadata for uploaded inputs and generated outputs."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )

    @classmethod
    def create_upload(
        cls,
        media_type: AssetMediaType,
        original_filename: str,
        stored_filename: str,
        content_type: str,
        size_bytes: int,
        checksum_sha256: str,
        relative_path: str,
    ) -> "Asset":
        return cls(
            kind=AssetKind.UPLOAD.value,
            media_type=media_type.value,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            relative_path=relative_path,
        )

    @classmethod
    def create_output(
        cls,
        media_type: AssetMediaType,
        original_filename: str,
        stored_filename: str,
        content_type: str,
        size_bytes: int,
        checksum_sha256: str,
        relative_path: str,
    ) -> "Asset":
        return cls(
            kind=AssetKind.OUTPUT.value,
            media_type=media_type.value,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            relative_path=relative_path,
        )
