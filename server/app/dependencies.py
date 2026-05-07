"""Application dependency providers for API and service layers."""

from collections.abc import AsyncIterator

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.comfy.client import ComfyUIClient
from app.comfy.outputs import ComfyUIOutputParser
from app.comfy.tracking import ComfyUIJobTracker
from app.comfy.websocket import ComfyUIWebSocketListener
from app.core.config import Settings
from app.core.redis import RedisClientProvider
from app.database.session import DatabaseSessionManager
from app.queue.celery_app import celery_app
from app.queue.service import QueueService
from app.services.health import HealthService
from app.services.workflow_execution import WorkflowExecutionService
from app.socket.publisher import SocketEventPublisher
from app.auth.service import AuthService
from app.schemas.auth import Principal
from app.workflows.builder import WorkflowBuilder

bearer_scheme: HTTPBearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_database_manager(request: Request) -> DatabaseSessionManager:
    return request.app.state.database_manager


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    database_manager: DatabaseSessionManager = get_database_manager(request)
    async for session in database_manager.session():
        yield session


def get_auth_service(
    request: Request,
    session: AsyncSession = Depends(get_database_session),
) -> AuthService:
    return AuthService(get_settings(request), session)


async def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Header(default=None, alias="X-API-Key"),
    auth_service: AuthService = Depends(get_auth_service),
) -> Principal:
    if credentials is not None:
        return await auth_service.get_principal_from_token(credentials.credentials)

    if api_key is not None:
        return await auth_service.get_principal_from_api_key(api_key)

    raise auth_service._invalid_credentials()


async def require_admin_principal(
    principal: Principal = Depends(require_principal),
) -> Principal:
    if principal.is_admin:
        return principal

    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges are required.",
    )


def get_redis_provider(request: Request) -> RedisClientProvider:
    return request.app.state.redis_provider


def get_redis_client(request: Request) -> Redis:
    redis_provider: RedisClientProvider = get_redis_provider(request)
    return redis_provider.get_client()


def get_health_service(request: Request) -> HealthService:
    settings: Settings = get_settings(request)
    database_manager: DatabaseSessionManager = get_database_manager(request)
    redis_provider: RedisClientProvider = get_redis_provider(request)
    return HealthService(
        settings=settings,
        database_manager=database_manager,
        redis_provider=redis_provider,
        comfy_client=get_comfy_client(request),
    )


def get_comfy_client(request: Request) -> ComfyUIClient:
    return request.app.state.comfy_client


def get_workflow_builder(request: Request) -> WorkflowBuilder:
    settings: Settings = get_settings(request)
    return WorkflowBuilder(settings)


def get_comfy_job_tracker(request: Request) -> ComfyUIJobTracker:
    settings: Settings = get_settings(request)
    redis_client: Redis = get_redis_client(request)
    return ComfyUIJobTracker(redis_client, settings)


def get_workflow_execution_service(request: Request) -> WorkflowExecutionService:
    settings: Settings = get_settings(request)
    comfy_client: ComfyUIClient = get_comfy_client(request)
    return WorkflowExecutionService(
        settings=settings,
        workflow_builder=get_workflow_builder(request),
        comfy_client=comfy_client,
        websocket_listener=ComfyUIWebSocketListener(settings),
        output_parser=ComfyUIOutputParser(comfy_client),
        job_tracker=get_comfy_job_tracker(request),
        event_publisher=SocketEventPublisher(settings),
    )


def get_queue_service(request: Request) -> QueueService:
    settings: Settings = get_settings(request)
    redis_client: Redis = get_redis_client(request)
    comfy_client: ComfyUIClient = get_comfy_client(request)
    return QueueService(
        settings=settings,
        celery_app=celery_app,
        redis_client=redis_client,
        comfy_client=comfy_client,
        job_tracker=ComfyUIJobTracker(redis_client, settings),
        event_publisher=SocketEventPublisher(settings),
    )
