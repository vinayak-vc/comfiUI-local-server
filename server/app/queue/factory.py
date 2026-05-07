"""Factory helpers for queue worker service composition."""

from redis.asyncio import Redis

from app.comfy.client import ComfyUIClient
from app.comfy.outputs import ComfyUIOutputParser
from app.comfy.tracking import ComfyUIJobTracker
from app.comfy.websocket import ComfyUIWebSocketListener
from app.core.config import Settings, get_settings
from app.services.workflow_execution import WorkflowExecutionService
from app.socket.publisher import SocketEventPublisher
from app.workflows.builder import WorkflowBuilder


class WorkerServiceFactory:
    """Builds worker-local service instances for Celery tasks."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings if settings is not None else get_settings()

    async def create_execution_service(self) -> tuple[WorkflowExecutionService, ComfyUIClient, Redis]:
        redis_client: Redis = Redis.from_url(
            self._settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=self._settings.redis_socket_timeout_seconds,
        )
        comfy_client: ComfyUIClient = ComfyUIClient(self._settings)
        job_tracker: ComfyUIJobTracker = ComfyUIJobTracker(redis_client, self._settings)
        execution_service: WorkflowExecutionService = WorkflowExecutionService(
            settings=self._settings,
            workflow_builder=WorkflowBuilder(self._settings),
            comfy_client=comfy_client,
            websocket_listener=ComfyUIWebSocketListener(self._settings),
            output_parser=ComfyUIOutputParser(comfy_client),
            job_tracker=job_tracker,
            event_publisher=SocketEventPublisher(self._settings),
        )
        return execution_service, comfy_client, redis_client
