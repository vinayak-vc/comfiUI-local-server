"""Job tracker lifecycle guard tests."""

from __future__ import annotations

import pytest

from app.comfy.tracking import ComfyUIJobTracker
from app.core.config import Settings
from app.schemas.comfy import GenerationMode, JobStatus, OutputAsset

pytestmark = pytest.mark.asyncio


class MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value


async def test_completed_job_cannot_be_downgraded_to_retrying() -> None:
    tracker: ComfyUIJobTracker = ComfyUIJobTracker(MemoryRedis(), Settings())
    await tracker.create("job-id", GenerationMode.TEXT_TO_IMAGE)
    await tracker.mark_completed(
        "job-id",
        [
            OutputAsset(
                filename="ComfyUI_00033_.png",
                subfolder="",
                type="output",
                url="/outputs/ComfyUI_00033_.png",
                media_type="image",
            )
        ],
    )

    job = await tracker.mark_retrying("job-id", "Asset file not found.", retry_count=1)

    assert job.status == JobStatus.COMPLETED
    assert job.retry_count == 0
    assert job.error is None
    assert len(job.outputs) == 1


async def test_completed_job_cannot_be_downgraded_to_failed() -> None:
    tracker: ComfyUIJobTracker = ComfyUIJobTracker(MemoryRedis(), Settings())
    await tracker.create("job-id", GenerationMode.TEXT_TO_IMAGE)
    await tracker.mark_completed("job-id", [])

    job = await tracker.mark_failed("job-id", "late bookkeeping failure")

    assert job.status == JobStatus.COMPLETED
    assert job.error is None
