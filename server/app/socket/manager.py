"""Socket.IO connection and room subscription manager."""

import asyncio
from typing import Any

import socketio
import structlog
from redis.asyncio import Redis

from app.comfy.tracking import ComfyUIJobTracker
from app.core.config import Settings
from app.schemas.comfy import TrackedJob
from app.socket.events import SocketEvent, job_room
from app.socket.publisher import SocketEventPublisher


class SocketConnectionManager:
    """Manages client connections and job room memberships."""

    def __init__(self, socket_server: socketio.AsyncServer, settings: Settings) -> None:
        self._socket_server: socketio.AsyncServer = socket_server
        self._settings: Settings = settings
        self._client_rooms: dict[str, set[str]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._publisher: SocketEventPublisher = SocketEventPublisher(settings)
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger("socket_manager")

    async def connect(self, sid: str) -> None:
        async with self._lock:
            self._client_rooms[sid] = set()

        await self._socket_server.emit(
            SocketEvent.CONNECTED.value,
            {"sid": sid},
            room=sid,
        )
        self._logger.info("socket_client_connected", sid=sid)

    async def disconnect(self, sid: str) -> None:
        async with self._lock:
            rooms: set[str] = self._client_rooms.pop(sid, set())

        for room in rooms:
            await self._socket_server.leave_room(sid, room)

        self._logger.info("socket_client_disconnected", sid=sid, rooms=len(rooms))

    async def subscribe_job(self, sid: str, payload: Any) -> None:
        job_id: str | None = self._extract_job_id(payload)
        if job_id is None:
            await self._emit_subscription_error(sid, "job_id is required.")
            return

        room: str = job_room(job_id)
        await self._socket_server.enter_room(sid, room)
        async with self._lock:
            self._client_rooms.setdefault(sid, set()).add(room)

        await self._socket_server.emit(
            SocketEvent.SUBSCRIPTION_READY.value,
            {"job_id": job_id},
            room=sid,
        )
        await self._emit_current_snapshot(sid, job_id)
        self._logger.info("socket_job_subscribed", sid=sid, job_id=job_id)

    async def unsubscribe_job(self, sid: str, payload: Any) -> None:
        job_id: str | None = self._extract_job_id(payload)
        if job_id is None:
            await self._emit_subscription_error(sid, "job_id is required.")
            return

        room: str = job_room(job_id)
        await self._socket_server.leave_room(sid, room)
        async with self._lock:
            rooms: set[str] = self._client_rooms.setdefault(sid, set())
            rooms.discard(room)

        self._logger.info("socket_job_unsubscribed", sid=sid, job_id=job_id)

    async def _emit_current_snapshot(self, sid: str, job_id: str) -> None:
        redis_client: Redis = Redis.from_url(
            self._settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=self._settings.redis_socket_timeout_seconds,
        )
        try:
            tracker: ComfyUIJobTracker = ComfyUIJobTracker(redis_client, self._settings)
            job: TrackedJob | None = await tracker.get(job_id)
            if job is not None:
                await self._publisher.emit_snapshot(sid, job)
        finally:
            await redis_client.aclose()

    async def _emit_subscription_error(self, sid: str, message: str) -> None:
        await self._socket_server.emit(
            SocketEvent.SUBSCRIPTION_ERROR.value,
            {"message": message},
            room=sid,
        )

    def _extract_job_id(self, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None

        job_id: Any = payload.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            return None
        return job_id
