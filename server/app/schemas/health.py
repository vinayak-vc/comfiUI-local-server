"""Health check response schemas."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy"]
    detail: str | None = None


class HealthCheckResponse(BaseModel):
    service: str
    version: str
    environment: str
    ready: bool
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    components: list[ComponentHealth]
