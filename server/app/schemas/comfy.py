"""Schemas for ComfyUI workflow execution."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

DEFAULT_FLUX_SCHNELL_PROMPT: str = (
    "a cinematic robot chef in a neon kitchen, high detail, soft studio lighting"
)


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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": DEFAULT_FLUX_SCHNELL_PROMPT,
                    "negative_prompt": "",
                    "seed": 173805153958730,
                    "model": "flux1-schnell-fp8.safetensors",
                    "sampler": "euler",
                    "scheduler": "simple",
                    "steps": 4,
                    "cfg": 1,
                    "denoise": 1,
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1,
                    "loras": [],
                    "extra_parameters": {},
                }
            ]
        }
    )

    prompt: str = Field(
        default=DEFAULT_FLUX_SCHNELL_PROMPT,
        description="Positive text prompt injected into Flux Schnell node 6.",
    )
    negative_prompt: str | None = Field(
        default="",
        description="Negative prompt injected into node 33. Flux Schnell commonly uses an empty negative prompt.",
    )
    seed: int | None = Field(
        default=173805153958730,
        description="KSampler seed for reproducible output. Change it for a different image.",
    )
    model: str | None = Field(
        default="flux1-schnell-fp8.safetensors",
        description="Checkpoint name injected into CheckpointLoaderSimple node 30.",
    )
    sampler: str | None = Field(default="euler", description="KSampler sampler_name for node 31.")
    scheduler: str | None = Field(default="simple", description="KSampler scheduler for node 31.")
    steps: int | None = Field(default=4, ge=1, description="Flux Schnell is designed for low step counts; default is 4.")
    cfg: float | None = Field(default=1, ge=0, description="Classifier-free guidance scale. Flux Schnell default is 1.")
    denoise: float | None = Field(default=1, ge=0, le=1, description="Denoise strength for the KSampler.")
    width: int | None = Field(default=1024, ge=1, description="Generated image width injected into EmptySD3LatentImage node 27.")
    height: int | None = Field(default=1024, ge=1, description="Generated image height injected into EmptySD3LatentImage node 27.")
    batch_size: int | None = Field(default=1, ge=1, description="Number of images generated in one workflow run.")
    input_image: str | None = Field(default=None, description="Reserved for image-to-image workflows; unused by flux_schnell.")
    input_video: str | None = Field(default=None, description="Reserved for video workflows; unused by flux_schnell.")
    loras: list[LoraInjection] = Field(
        default_factory=list,
        description="LoRA injections. Leave empty for flux_schnell because the workflow has no LoraLoader nodes.",
    )
    extra_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Advanced node override map using node_id.input keys, for example {'31.steps': 6}.",
    )


class WorkflowExecutionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {},
                {
                    "parameters": {
                        "prompt": DEFAULT_FLUX_SCHNELL_PROMPT,
                        "seed": 12345,
                    }
                },
            ]
        }
    )

    mode: GenerationMode = Field(default=GenerationMode.TEXT_TO_IMAGE, description="Generation mode. Defaults to text-to-image.")
    parameters: WorkflowRuntimeParameters = Field(
        default_factory=WorkflowRuntimeParameters,
        description="Runtime parameters. Omit the object or individual fields to use Flux Schnell defaults.",
    )
    workflow_name: str | None = Field(
        default="flux_schnell",
        description="Workflow template filename without .json. Defaults to workflow/flux_schnell.json.",
    )


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
