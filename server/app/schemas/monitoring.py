"""Monitoring and dashboard response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.comfy import JobStatus, TrackedJob


class JobListResponse(BaseModel):
    """Recent tracked jobs for dashboard display."""

    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    status: JobStatus | None = None
    jobs: list[TrackedJob]


class QueueSnapshotMeta(BaseModel):
    """Optional metadata about queue snapshot timing."""

    as_of: datetime
    source: Literal["redis_celery_inspection"] = "redis_celery_inspection"


class JobCountsResponse(BaseModel):
    """Counts of tracked jobs grouped by current status."""

    counts: dict[JobStatus, int]


class LogTailResponse(BaseModel):
    """Tail of the configured application log file."""

    lines: list[str]
    truncated: bool = False

