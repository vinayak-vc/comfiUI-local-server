"""Celery tasks for queued ComfyUI workflow execution."""

import asyncio
from typing import Any

import structlog
from celery import Task
from celery.exceptions import MaxRetriesExceededError, Retry, SoftTimeLimitExceeded
from redis.asyncio import Redis

from app.comfy.client import ComfyUIClient
from app.comfy.exceptions import WorkflowTemplateError
from app.comfy.tracking import ComfyUIJobTracker
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database.session import DatabaseSessionManager
from app.queue.celery_app import celery_app
from app.queue.factory import WorkerServiceFactory
from app.schemas.comfy import JobStatus, OutputAsset, TrackedJob, WorkflowExecutionRequest
from app.services.workflow_execution import WorkflowExecutionService
from app.socket.publisher import SocketEventPublisher
from app.storage.exceptions import AssetNotFoundError
from app.storage.service import StorageService


@celery_app.task(
    bind=True,
    name="app.queue.tasks.render_workflow",
    acks_late=True,
)
def render_workflow_task(self: Task, job_id: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    settings: Settings = get_settings()
    configure_logging(settings)
    logger: structlog.stdlib.BoundLogger = structlog.get_logger("celery_task")

    try:
        return asyncio.run(_execute_workflow_task(self, job_id, request_payload))
    except Retry:
        raise
    except WorkflowTemplateError as exc:
        logger.warning("queued_workflow_template_invalid", job_id=job_id, error=str(exc))
        return asyncio.run(_mark_task_failed(job_id, str(exc)))
    except SoftTimeLimitExceeded as exc:
        return asyncio.run(_handle_task_failure(self, job_id, "Workflow execution timed out.", exc))
    except Exception as exc:
        logger.exception("queued_workflow_task_failed", job_id=job_id)
        return asyncio.run(_handle_task_failure(self, job_id, str(exc), exc))


async def _execute_workflow_task(
    task: Task,
    job_id: str,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    execution_service: WorkflowExecutionService
    comfy_client: ComfyUIClient
    redis_client: Redis
    execution_service, comfy_client, redis_client = await WorkerServiceFactory().create_execution_service()

    try:
        request: WorkflowExecutionRequest = WorkflowExecutionRequest.model_validate(request_payload)
        result = await execution_service.execute_job(job_id, request, mark_failed_on_error=False)
        await _register_output_assets(result.outputs)
        return result.model_dump(mode="json")
    finally:
        await comfy_client.close()
        await redis_client.aclose()


async def _register_output_assets(outputs: list[OutputAsset]) -> None:
    if not outputs:
        return

    settings: Settings = get_settings()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger("celery_task")
    database_manager: DatabaseSessionManager = DatabaseSessionManager(settings)
    await database_manager.connect()
    try:
        async for session in database_manager.session():
            storage_service: StorageService = StorageService(settings, session)
            for output in outputs:
                relative_path: str = _output_relative_path(output)
                try:
                    await storage_service.register_output(
                        relative_path=relative_path,
                        content_type=None,
                        original_filename=output.filename,
                    )
                except AssetNotFoundError:
                    logger.warning(
                        "output_asset_registration_skipped",
                        filename=output.filename,
                        relative_path=relative_path,
                        reason="file_not_found_in_backend_outputs_path",
                    )
    finally:
        await database_manager.close()


def _output_relative_path(output: OutputAsset) -> str:
    if output.subfolder:
        return f"{output.subfolder.strip('/')}/{output.filename}"
    return output.filename


async def _handle_task_failure(
    task: Task,
    job_id: str,
    error_message: str,
    exc: Exception,
) -> dict[str, Any]:
    settings: Settings = get_settings()
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=settings.redis_socket_timeout_seconds,
    )
    tracker: ComfyUIJobTracker = ComfyUIJobTracker(redis_client, settings)
    publisher: SocketEventPublisher = SocketEventPublisher(settings)

    try:
        job: TrackedJob | None = await tracker.get(job_id)
        if job is not None and job.status == JobStatus.CANCELLED:
            return job.model_dump(mode="json")

        retry_count: int = int(task.request.retries) + 1
        if task.request.retries < settings.celery_task_max_retries:
            await tracker.mark_retrying(job_id, error_message, retry_count)
            raise task.retry(
                exc=exc,
                countdown=settings.celery_task_retry_delay_seconds,
                max_retries=settings.celery_task_max_retries,
            )

        failed_job: TrackedJob = await tracker.mark_failed(job_id, error_message)
        await publisher.emit_job_failed(job_id, error_message)
        return failed_job.model_dump(mode="json")
    except MaxRetriesExceededError:
        failed_job = await tracker.mark_failed(job_id, error_message)
        await publisher.emit_job_failed(job_id, error_message)
        return failed_job.model_dump(mode="json")
    finally:
        await redis_client.aclose()


async def _mark_task_failed(job_id: str, error_message: str) -> dict[str, Any]:
    settings: Settings = get_settings()
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=settings.redis_socket_timeout_seconds,
    )
    tracker: ComfyUIJobTracker = ComfyUIJobTracker(redis_client, settings)
    publisher: SocketEventPublisher = SocketEventPublisher(settings)

    try:
        failed_job: TrackedJob = await tracker.mark_failed(job_id, error_message)
        await publisher.emit_job_failed(job_id, error_message)
        return failed_job.model_dump(mode="json")
    finally:
        await redis_client.aclose()
