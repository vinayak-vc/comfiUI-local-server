"""Redis-backed job tracking for ComfyUI executions."""

from datetime import UTC, datetime

from redis.asyncio import Redis

from app.core.config import Settings
from app.schemas.comfy import GenerationMode, JobStatus, OutputAsset, TrackedJob


class ComfyUIJobTracker:
    """Stores ComfyUI job state in Redis for API and worker visibility."""

    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self._redis_client: Redis = redis_client
        self._ttl_seconds: int = settings.comfyui_job_ttl_seconds

    async def create(self, job_id: str, mode: GenerationMode) -> TrackedJob:
        job: TrackedJob = TrackedJob(
            job_id=job_id,
            mode=mode,
            status=JobStatus.QUEUED,
        )
        await self._save(job)
        return job

    async def get(self, job_id: str) -> TrackedJob | None:
        raw_value: str | None = await self._redis_client.get(self._key(job_id))
        if raw_value is None:
            return None
        return TrackedJob.model_validate_json(raw_value)

    async def attach_task(self, job_id: str, task_id: str) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        job.task_id = task_id
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def mark_running(self, job_id: str, prompt_id: str) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        if job.status == JobStatus.CANCELLED:
            return job
        job.prompt_id = prompt_id
        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def update_progress(
        self,
        job_id: str,
        current: int | None,
        maximum: int | None,
    ) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        if job.status == JobStatus.CANCELLED:
            return job
        job.status = JobStatus.RUNNING
        job.progress_current = current
        job.progress_maximum = maximum
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def mark_retrying(self, job_id: str, error: str, retry_count: int) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        if job.status == JobStatus.CANCELLED:
            return job
        job.status = JobStatus.RETRYING
        job.error = error
        job.retry_count = retry_count
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def mark_completed(self, job_id: str, outputs: list[OutputAsset]) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        if job.status == JobStatus.CANCELLED:
            return job
        job.status = JobStatus.COMPLETED
        job.outputs = outputs
        job.error = None
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def mark_failed(self, job_id: str, error: str) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        if job.status == JobStatus.CANCELLED:
            return job
        job.status = JobStatus.FAILED
        job.error = error
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def mark_cancelled(self, job_id: str) -> TrackedJob:
        job: TrackedJob = await self._require_job(job_id)
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now(UTC)
        await self._save(job)
        return job

    async def is_cancelled(self, job_id: str) -> bool:
        job: TrackedJob | None = await self.get(job_id)
        return job is not None and job.status == JobStatus.CANCELLED

    async def count_by_status(self) -> dict[JobStatus, int]:
        counts: dict[JobStatus, int] = {status: 0 for status in JobStatus}
        async for key in self._redis_client.scan_iter(match=self._key("*")):
            raw_value: str | None = await self._redis_client.get(key)
            if raw_value is None:
                continue

            try:
                job: TrackedJob = TrackedJob.model_validate_json(raw_value)
            except ValueError:
                continue

            counts[job.status] += 1
        return counts

    async def list_jobs(
        self,
        limit: int,
        offset: int = 0,
        status: JobStatus | None = None,
    ) -> tuple[list[TrackedJob], int]:
        """
        Lists jobs from Redis for dashboard display.

        Note: Redis SCAN is used (not sorted server-side), so we sort by `updated_at` in memory.
        """

        if limit < 1:
            return ([], 0)

        jobs: list[TrackedJob] = []
        async for key in self._redis_client.scan_iter(match=self._key("*")):
            raw_value: str | None = await self._redis_client.get(key)
            if raw_value is None:
                continue

            try:
                job: TrackedJob = TrackedJob.model_validate_json(raw_value)
            except ValueError:
                continue

            if status is not None and job.status != status:
                continue

            jobs.append(job)

        jobs.sort(key=lambda j: j.updated_at, reverse=True)
        total: int = len(jobs)

        start: int = min(max(offset, 0), total)
        end: int = min(start + limit, total)
        return (jobs[start:end], total)

    async def _require_job(self, job_id: str) -> TrackedJob:
        job: TrackedJob | None = await self.get(job_id)
        if job is None:
            raise KeyError(f"Tracked job does not exist: {job_id}")
        return job

    async def _save(self, job: TrackedJob) -> None:
        await self._redis_client.set(
            self._key(job.job_id),
            job.model_dump_json(),
            ex=self._ttl_seconds,
        )

    def _key(self, job_id: str) -> str:
        return f"comfyui:job:{job_id}"
