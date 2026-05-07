"""Schemas for ComfyUI workflow execution."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class GenerationMode(StrEnum):
    TEXT_TO_IMAGE = "t2i"
    IMAGE_TO_IMAGE = "i2i"
    TEXT_TO_VIDEO = "t2v"
    IMAGE_TO_VIDEO = "i2v"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LoraInjection(BaseModel):
    name: str
    strength_model: float = 1.0
    strength_clip: float = 1.0


class WorkflowRuntimeParameters(BaseModel):
    prompt: str
    negative_prompt: str | None = None
    seed: int | None = None
    model: str | None = None
    sampler: str | None = None
    scheduler: str | None = None
    steps: int | None = Field(default=None, ge=1)
    cfg: float | None = Field(default=None, ge=0)
    denoise: float | None = Field(default=None, ge=0, le=1)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    batch_size: int | None = Field(default=None, ge=1)
    input_image: str | None = None
    input_video: str | None = None
    loras: list[LoraInjection] = Field(default_factory=list)
    extra_parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionRequest(BaseModel):
    mode: GenerationMode
    parameters: WorkflowRuntimeParameters
    workflow_name: str | None = None


class OutputAsset(BaseModel):
    filename: str
    subfolder: str
    type: str
    url: HttpUrl | str
    media_type: str


class ProgressEvent(BaseModel):
    job_id: str
    prompt_id: str | None = None
    status: JobStatus
    node_id: str | None = None
    current: int | None = None
    maximum: int | None = None
    message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowExecutionResult(BaseModel):
    job_id: str
    prompt_id: str
    status: JobStatus
    outputs: list[OutputAsset]
    events: list[ProgressEvent]
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class TrackedJob(BaseModel):
    job_id: str
    task_id: str | None = None
    prompt_id: str | None = None
    mode: GenerationMode
    status: JobStatus
    retry_count: int = 0
    progress_current: int | None = None
    progress_maximum: int | None = None
    error: str | None = None
    outputs: list[OutputAsset] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueueSubmissionResponse(BaseModel):
    job: TrackedJob


class QueueMonitoringResponse(BaseModel):
    queue_name: str
    pending_count: int
    active_count: int
    reserved_count: int
    scheduled_count: int
    worker_concurrency: int
    gpu_safe: bool
    persisted_status_counts: dict[JobStatus, int]
