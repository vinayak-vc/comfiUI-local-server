"""Async Socket.IO event publisher for job realtime updates."""

from typing import Any

import socketio

from app.core.config import Settings
from app.schemas.comfy import JobStatus, OutputAsset, TrackedJob
from app.socket.events import SocketEvent, job_room


class SocketEventPublisher:
    """Publishes job events to Socket.IO rooms through Redis."""

    def __init__(self, settings: Settings) -> None:
        self._manager: socketio.AsyncRedisManager = socketio.AsyncRedisManager(
            settings.redis_url,
            channel=settings.socketio_channel,
            write_only=True,
        )

    async def emit_job_queued(self, job: TrackedJob) -> None:
        await self._emit(SocketEvent.JOB_QUEUED, job.job_id, self._job_payload(job))

    async def emit_job_started(self, job: TrackedJob) -> None:
        await self._emit(SocketEvent.JOB_STARTED, job.job_id, self._job_payload(job))

    async def emit_progress_update(
        self,
        job_id: str,
        prompt_id: str,
        current: int | None,
        maximum: int | None,
        node_id: str | None,
    ) -> None:
        await self._emit(
            SocketEvent.PROGRESS_UPDATE,
            job_id,
            {
                "job_id": job_id,
                "prompt_id": prompt_id,
                "current": current,
                "maximum": maximum,
                "node_id": node_id,
            },
        )

    async def emit_preview_image(
        self,
        job_id: str,
        prompt_id: str,
        image_data: str,
        encoding: str,
    ) -> None:
        await self._emit(
            SocketEvent.PREVIEW_IMAGE,
            job_id,
            {
                "job_id": job_id,
                "prompt_id": prompt_id,
                "encoding": encoding,
                "data": image_data,
            },
        )

    async def emit_preview_video(
        self,
        job_id: str,
        prompt_id: str,
        video_data: str,
        encoding: str,
    ) -> None:
        await self._emit(
            SocketEvent.PREVIEW_VIDEO,
            job_id,
            {
                "job_id": job_id,
                "prompt_id": prompt_id,
                "encoding": encoding,
                "data": video_data,
            },
        )

    async def emit_job_completed(self, job_id: str, prompt_id: str, outputs: list[OutputAsset]) -> None:
        await self._emit(
            SocketEvent.JOB_COMPLETED,
            job_id,
            {
                "job_id": job_id,
                "prompt_id": prompt_id,
                "outputs": [output.model_dump(mode="json") for output in outputs],
            },
        )

    async def emit_job_failed(self, job_id: str, error: str) -> None:
        await self._emit(
            SocketEvent.JOB_FAILED,
            job_id,
            {
                "job_id": job_id,
                "error": error,
            },
        )

    async def emit_snapshot(self, sid: str, job: TrackedJob) -> None:
        event: SocketEvent = self._event_for_status(job.status)
        await self._manager.emit(event.value, self._job_payload(job), room=sid)

    async def _emit(self, event: SocketEvent, job_id: str, payload: dict[str, Any]) -> None:
        await self._manager.emit(event.value, payload, room=job_room(job_id))

    def _job_payload(self, job: TrackedJob) -> dict[str, Any]:
        return job.model_dump(mode="json")

    def _event_for_status(self, status: JobStatus) -> SocketEvent:
        if status == JobStatus.QUEUED:
            return SocketEvent.JOB_QUEUED
        if status == JobStatus.RUNNING or status == JobStatus.RETRYING:
            return SocketEvent.JOB_STARTED
        if status == JobStatus.COMPLETED:
            return SocketEvent.JOB_COMPLETED
        if status == JobStatus.FAILED:
            return SocketEvent.JOB_FAILED
        return SocketEvent.JOB_FAILED
