"""Workflow execution service for ComfyUI-backed generation modes."""

import asyncio
import base64
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

from app.comfy.client import ComfyUIClient
from app.comfy.exceptions import ComfyUIError, WorkflowExecutionError, WorkflowTemplateError
from app.comfy.outputs import ComfyUIOutputParser
from app.comfy.tracking import ComfyUIJobTracker
from app.comfy.websocket import ComfyUIWebSocketListener
from app.core.config import Settings
from app.schemas.comfy import (
    JobStatus,
    OutputAsset,
    ProgressEvent,
    WorkflowExecutionRequest,
    WorkflowExecutionResult,
    TrackedJob,
)
from app.socket.publisher import SocketEventPublisher
from app.workflows.builder import WorkflowBuilder


class WorkflowExecutionService:
    """Builds, queues, tracks, and resolves ComfyUI workflow executions."""

    def __init__(
        self,
        settings: Settings,
        workflow_builder: WorkflowBuilder,
        comfy_client: ComfyUIClient,
        websocket_listener: ComfyUIWebSocketListener,
        output_parser: ComfyUIOutputParser,
        job_tracker: ComfyUIJobTracker,
        event_publisher: SocketEventPublisher | None = None,
    ) -> None:
        self._settings: Settings = settings
        self._workflow_builder: WorkflowBuilder = workflow_builder
        self._comfy_client: ComfyUIClient = comfy_client
        self._websocket_listener: ComfyUIWebSocketListener = websocket_listener
        self._output_parser: ComfyUIOutputParser = output_parser
        self._job_tracker: ComfyUIJobTracker = job_tracker
        self._event_publisher: SocketEventPublisher | None = event_publisher
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger("workflow_execution")

    async def execute(self, request: WorkflowExecutionRequest) -> WorkflowExecutionResult:
        job_id: str = str(uuid4())
        job: TrackedJob = await self._job_tracker.create(job_id, request.mode)
        if self._event_publisher is not None:
            await self._event_publisher.emit_job_queued(job)
        return await self.execute_job(job_id, request)

    async def execute_job(
        self,
        job_id: str,
        request: WorkflowExecutionRequest,
        mark_failed_on_error: bool = True,
    ) -> WorkflowExecutionResult:
        client_id: str = str(uuid4())
        started_at: datetime = datetime.now(UTC)
        events: list[ProgressEvent] = []

        try:
            await self._raise_if_cancelled(job_id)
            workflow: dict[str, Any] = self._workflow_builder.build(
                mode=request.mode,
                parameters=request.parameters,
                workflow_name=request.workflow_name,
            )
            prompt_id: str = await self._comfy_client.queue_prompt(workflow, client_id)
            await self._raise_if_cancelled(job_id)
            running_job: TrackedJob = await self._job_tracker.mark_running(job_id, prompt_id)
            if self._event_publisher is not None:
                await self._event_publisher.emit_job_started(running_job)
            events.append(
                ProgressEvent(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    status=JobStatus.QUEUED,
                    message="Workflow queued in ComfyUI.",
                )
            )

            await asyncio.wait_for(
                self._listen_for_progress(job_id, prompt_id, client_id, events),
                timeout=self._settings.comfyui_execution_timeout_seconds,
            )

            await self._raise_if_cancelled(job_id)
            history: dict[str, Any] = await self._comfy_client.get_history(prompt_id)
            self._raise_for_history_error(history)
            outputs: list[OutputAsset] = self._output_parser.parse(history)
            await self._job_tracker.mark_completed(job_id, outputs)
            if self._event_publisher is not None:
                await self._event_publisher.emit_job_completed(job_id, prompt_id, outputs)

            completed_at: datetime = datetime.now(UTC)
            events.append(
                ProgressEvent(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    status=JobStatus.COMPLETED,
                    message="Workflow completed.",
                )
            )
            return WorkflowExecutionResult(
                job_id=job_id,
                prompt_id=prompt_id,
                status=JobStatus.COMPLETED,
                outputs=outputs,
                events=events,
                started_at=started_at,
                completed_at=completed_at,
            )
        except WorkflowTemplateError as exc:
            error_message: str = str(exc)
            if mark_failed_on_error:
                await self._job_tracker.mark_failed(job_id, error_message)
                if self._event_publisher is not None:
                    await self._event_publisher.emit_job_failed(job_id, error_message)
            self._logger.warning("workflow_template_invalid", job_id=job_id, error=error_message)
            raise
        except Exception as exc:
            error_message: str = str(exc)
            if await self._job_tracker.is_cancelled(job_id):
                raise WorkflowExecutionError("Workflow execution was cancelled.") from exc
            if mark_failed_on_error:
                await self._job_tracker.mark_failed(job_id, error_message)
                if self._event_publisher is not None:
                    await self._event_publisher.emit_job_failed(job_id, error_message)
            self._logger.exception("workflow_execution_failed", job_id=job_id)
            raise WorkflowExecutionError(error_message) from exc

    async def get_job(self, job_id: str) -> TrackedJob | None:
        return await self._job_tracker.get(job_id)

    async def cancel(self, job_id: str) -> None:
        await self._comfy_client.interrupt()
        await self._job_tracker.mark_cancelled(job_id)

    async def _listen_for_progress(
        self,
        job_id: str,
        prompt_id: str,
        client_id: str,
        events: list[ProgressEvent],
    ) -> None:
        async for message in self._websocket_listener.listen(client_id, prompt_id):
            await self._raise_if_cancelled(job_id)
            progress_event: ProgressEvent | None = await self._handle_progress_message(
                job_id,
                prompt_id,
                message,
            )
            if progress_event is not None:
                events.append(progress_event)

    async def _handle_progress_message(
        self,
        job_id: str,
        prompt_id: str,
        message: dict[str, Any],
    ) -> ProgressEvent | None:
        message_type: Any = message.get("type")
        data: Any = message.get("data")
        if not isinstance(message_type, str) or not isinstance(data, dict):
            return None

        if message_type == "progress":
            current: int | None = self._as_int(data.get("value"))
            maximum: int | None = self._as_int(data.get("max"))
            await self._job_tracker.update_progress(job_id, current, maximum)
            if self._event_publisher is not None:
                await self._event_publisher.emit_progress_update(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    current=current,
                    maximum=maximum,
                    node_id=None,
                )
            return ProgressEvent(
                job_id=job_id,
                prompt_id=prompt_id,
                status=JobStatus.RUNNING,
                current=current,
                maximum=maximum,
            )

        if message_type == "executing":
            node_id: Any = data.get("node")
            if self._event_publisher is not None:
                await self._event_publisher.emit_progress_update(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    current=None,
                    maximum=None,
                    node_id=node_id if isinstance(node_id, str) else None,
                )
            return ProgressEvent(
                job_id=job_id,
                prompt_id=prompt_id,
                status=JobStatus.RUNNING,
                node_id=node_id if isinstance(node_id, str) else None,
            )

        if message_type == "execution_error":
            exception_message: Any = data.get("exception_message")
            error_message: str = exception_message if isinstance(exception_message, str) else "ComfyUI execution failed."
            raise WorkflowExecutionError(error_message)

        if message_type == "preview_image":
            preview_bytes: Any = data.get("bytes")
            if isinstance(preview_bytes, bytes) and self._event_publisher is not None:
                await self._event_publisher.emit_preview_image(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    image_data=base64.b64encode(preview_bytes).decode("ascii"),
                    encoding=self._settings.socketio_preview_encoding,
                )
            return None

        if message_type == "preview_video":
            preview_bytes = data.get("bytes")
            if isinstance(preview_bytes, bytes) and self._event_publisher is not None:
                await self._event_publisher.emit_preview_video(
                    job_id=job_id,
                    prompt_id=prompt_id,
                    video_data=base64.b64encode(preview_bytes).decode("ascii"),
                    encoding=self._settings.socketio_preview_encoding,
                )
            return None

        return None

    def _raise_for_history_error(self, history: dict[str, Any]) -> None:
        status: Any = history.get("status")
        if not isinstance(status, dict):
            return

        status_string: Any = status.get("status_str")
        completed: Any = status.get("completed")
        if status_string == "error" or completed is False:
            messages: Any = status.get("messages")
            raise ComfyUIError(f"ComfyUI workflow did not complete successfully: {messages}")

    def _as_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        return None

    async def _raise_if_cancelled(self, job_id: str) -> None:
        if await self._job_tracker.is_cancelled(job_id):
            await self._comfy_client.interrupt()
            raise WorkflowExecutionError("Workflow execution was cancelled.")
