from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, AsyncIterator

import pytest

from app.comfy.tracking import ComfyUIJobTracker
from app.core.config import Settings
from app.schemas.comfy import GenerationMode, JobStatus, TrackedJob


@dataclass(frozen=True)
class _RedisEntry:
    key: str
    value: str


class FakeRedis:
    def __init__(self, entries: list[_RedisEntry]) -> None:
        self._entries_by_key: dict[str, str] = {e.key: e.value for e in entries}
        self._keys: list[str] = [e.key for e in entries]

    def scan_iter(self, match: str) -> AsyncIterator[str]:
        async def gen() -> AsyncIterator[str]:
            # Match is ignored here because this is a deterministic unit test.
            for key in self._keys:
                yield key

        return gen()

    async def get(self, key: str) -> str | None:
        return self._entries_by_key.get(key)


pytestmark = pytest.mark.asyncio


async def test_list_jobs_sorts_filters_and_pages() -> None:
    base_time = datetime.now(UTC)

    job1 = TrackedJob(
        job_id="job-1",
        mode=GenerationMode.TEXT_TO_IMAGE,
        status=JobStatus.COMPLETED,
        updated_at=base_time - timedelta(minutes=1),
    )
    job2 = TrackedJob(
        job_id="job-2",
        mode=GenerationMode.TEXT_TO_IMAGE,
        status=JobStatus.RUNNING,
        updated_at=base_time - timedelta(seconds=30),
    )
    job3 = TrackedJob(
        job_id="job-3",
        mode=GenerationMode.TEXT_TO_IMAGE,
        status=JobStatus.COMPLETED,
        updated_at=base_time - timedelta(seconds=10),
    )

    settings = Settings()
    tracker = ComfyUIJobTracker(redis_client=FakeRedis([]), settings=settings)

    entries = [
        _RedisEntry(key=tracker._key(job1.job_id), value=job1.model_dump_json()),
        _RedisEntry(key=tracker._key(job2.job_id), value=job2.model_dump_json()),
        _RedisEntry(key=tracker._key(job3.job_id), value=job3.model_dump_json()),
    ]

    tracker = ComfyUIJobTracker(redis_client=FakeRedis(entries), settings=settings)

    jobs, total = await tracker.list_jobs(limit=10, offset=0, status=None)
    assert total == 3
    assert [j.job_id for j in jobs] == ["job-3", "job-2", "job-1"]

    completed_jobs, completed_total = await tracker.list_jobs(limit=10, offset=0, status=JobStatus.COMPLETED)
    assert completed_total == 2
    assert [j.job_id for j in completed_jobs] == ["job-3", "job-1"]

    paged_jobs, paged_total = await tracker.list_jobs(limit=1, offset=1, status=None)
    assert paged_total == 3
    assert [j.job_id for j in paged_jobs] == ["job-2"]

