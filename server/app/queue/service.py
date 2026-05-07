"""Queue orchestration service for Celery-backed workflow execution."""

from uuid import uuid4

import structlog
from celery import Celery
from celery.result import AsyncResult
from redis.asyncio import Redis

from app.comfy.client import ComfyUIClient
from app.comfy.tracking import ComfyUIJobTracker
from app.core.config import Settings
from app.queue.tasks import render_workflow_task
from app.schemas.comfy import (
    JobStatus,
    QueueMonitoringResponse,
    QueueSubmissionResponse,
    TrackedJob,
    WorkflowExecutionRequest,
)
from app.socket.publisher import SocketEventPublisher


class QueueService:
    """Submits, cancels, and monitors GPU-safe workflow jobs."""

    def __init__(
        self,
        settings: Settings,
        celery_app: Celery,
        redis_client: Redis,
        comfy_client: ComfyUIClient,
        job_tracker: ComfyUIJobTracker,
        event_publisher: SocketEventPublisher,
    ) -> None:
        self._settings: Settings = settings
        self._celery_app: Celery = celery_app
        self._redis_client: Redis = redis_client
        self._comfy_client: ComfyUIClient = comfy_client
        self._job_tracker: ComfyUIJobTracker = job_tracker
        self._event_publisher: SocketEventPublisher = event_publisher
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger("queue_service")

    async def submit(self, request: WorkflowExecutionRequest) -> QueueSubmissionResponse:
        job_id: str = str(uuid4())
        job: TrackedJob = await self._job_tracker.create(job_id, request.mode)
        async_result: AsyncResult = render_workflow_task.apply_async(
            args=[job_id, request.model_dump(mode="json")],
            queue=self._settings.celery_queue_name,
            routing_key=self._settings.celery_queue_name,
        )
        task_id: str = str(async_result.id)
        job = await self._job_tracker.attach_task(job_id, task_id)
        await self._event_publisher.emit_job_queued(job)
        self._logger.info(
            "workflow_job_submitted",
            job_id=job_id,
            task_id=task_id,
            mode=request.mode.value,
            queue=self._settings.celery_queue_name,
        )
        return QueueSubmissionResponse(job=job)

    async def get_job(self, job_id: str) -> TrackedJob | None:
        return await self._job_tracker.get(job_id)

    async def cancel(self, job_id: str) -> TrackedJob:
        job: TrackedJob | None = await self._job_tracker.get(job_id)
        if job is None:
            raise KeyError(f"Tracked job does not exist: {job_id}")

        if job.task_id is not None:
            self._celery_app.control.revoke(job.task_id, terminate=True, signal="SIGTERM")

        if job.status == JobStatus.RUNNING and job.prompt_id is not None:
            await self._comfy_client.interrupt()

        cancelled_job: TrackedJob = await self._job_tracker.mark_cancelled(job_id)
        await self._event_publisher.emit_job_failed(job_id, "Workflow execution was cancelled.")
        self._logger.info(
            "workflow_job_cancelled",
            job_id=job_id,
            task_id=job.task_id,
            previous_status=job.status.value,
        )
        return cancelled_job

    async def monitor(self) -> QueueMonitoringResponse:
        active_count: int = self._inspect_count("active")
        reserved_count: int = self._inspect_count("reserved")
        scheduled_count: int = self._inspect_count("scheduled")
        pending_count: int = await self._redis_client.llen(self._settings.celery_queue_name)
        persisted_status_counts: dict[JobStatus, int] = await self._job_tracker.count_by_status()

        response: QueueMonitoringResponse = QueueMonitoringResponse(
            queue_name=self._settings.celery_queue_name,
            pending_count=pending_count,
            active_count=active_count,
            reserved_count=reserved_count,
            scheduled_count=scheduled_count,
            worker_concurrency=self._settings.celery_worker_concurrency,
            gpu_safe=self._settings.celery_worker_concurrency == 1,
            persisted_status_counts=persisted_status_counts,
        )
        self._logger.info(
            "queue_monitor_snapshot",
            queue_name=response.queue_name,
            pending_count=response.pending_count,
            active_count=response.active_count,
            reserved_count=response.reserved_count,
            scheduled_count=response.scheduled_count,
        )
        return response

    def _inspect_count(self, section: str) -> int:
        inspector = self._celery_app.control.inspect(timeout=1)
        if section == "active":
            payload = inspector.active()
        elif section == "reserved":
            payload = inspector.reserved()
        else:
            payload = inspector.scheduled()

        if payload is None:
            return 0

        count: int = 0
        for tasks in payload.values():
            count += len(tasks)
        return count
