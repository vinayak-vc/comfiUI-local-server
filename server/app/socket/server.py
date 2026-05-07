"""Socket.IO ASGI server creation and event registration."""

import socketio

from app.core.config import Settings
from app.socket.events import SocketEvent
from app.socket.manager import SocketConnectionManager


def create_socketio_server(settings: Settings) -> socketio.AsyncServer:
    redis_manager: socketio.AsyncRedisManager = socketio.AsyncRedisManager(
        settings.redis_url,
        channel=settings.socketio_channel,
    )
    socket_server: socketio.AsyncServer = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=redis_manager,
        cors_allowed_origins=settings.socketio_allowed_origins or [],
        logger=False,
        engineio_logger=False,
    )
    connection_manager: SocketConnectionManager = SocketConnectionManager(socket_server, settings)

    @socket_server.event
    async def connect(sid: str, environ: dict[str, object], auth: object) -> bool:
        await connection_manager.connect(sid)
        return True

    @socket_server.event
    async def disconnect(sid: str) -> None:
        await connection_manager.disconnect(sid)

    @socket_server.on(SocketEvent.SUBSCRIBE_JOB.value)
    async def subscribe_job(sid: str, payload: object) -> None:
        await connection_manager.subscribe_job(sid, payload)

    @socket_server.on(SocketEvent.UNSUBSCRIBE_JOB.value)
    async def unsubscribe_job(sid: str, payload: object) -> None:
        await connection_manager.unsubscribe_job(sid, payload)

    return socket_server
