"""Socket.IO realtime configuration tests."""

import socketio

from app.core.config import Settings
from app.main import socket_app
from app.socket.events import SocketEvent, job_room
from app.socket.server import create_socketio_server


def test_job_room_uses_stable_prefix() -> None:
    assert job_room("abc") == "job:abc"


def test_required_socket_events_are_defined() -> None:
    assert SocketEvent.JOB_QUEUED.value == "job_queued"
    assert SocketEvent.JOB_STARTED.value == "job_started"
    assert SocketEvent.PROGRESS_UPDATE.value == "progress_update"
    assert SocketEvent.PREVIEW_IMAGE.value == "preview_image"
    assert SocketEvent.PREVIEW_VIDEO.value == "preview_video"
    assert SocketEvent.JOB_COMPLETED.value == "job_completed"
    assert SocketEvent.JOB_FAILED.value == "job_failed"


def test_socketio_server_uses_async_mode() -> None:
    socket_server: socketio.AsyncServer = create_socketio_server(Settings())

    assert socket_server.async_mode == "asgi"
    assert socket_app is not None
