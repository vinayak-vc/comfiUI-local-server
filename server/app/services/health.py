"""Health service coordinating infrastructure checks."""

from redis.asyncio import Redis

from app.comfy.client import ComfyUIClient
from app.core.config import Settings
from app.core.redis import RedisClientProvider
from app.database.session import DatabaseSessionManager
from app.schemas.health import ComponentHealth, HealthCheckResponse


class HealthService:
    """Builds liveness and readiness responses without route-level business logic."""

    def __init__(
        self,
        settings: Settings,
        database_manager: DatabaseSessionManager,
        redis_provider: RedisClientProvider,
        comfy_client: ComfyUIClient | None = None,
    ) -> None:
        self._settings: Settings = settings
        self._database_manager: DatabaseSessionManager = database_manager
        self._redis_provider: RedisClientProvider = redis_provider
        self._comfy_client: ComfyUIClient | None = comfy_client

    def live(self) -> HealthCheckResponse:
        return HealthCheckResponse(
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.environment,
            ready=True,
            components=[
                ComponentHealth(name="application", status="healthy"),
            ],
        )

    async def check(self) -> HealthCheckResponse:
        components: list[ComponentHealth] = [
            await self._check_database(),
            await self._check_redis(),
            await self._check_comfyui(),
        ]
        ready: bool = all(component.status == "healthy" for component in components)

        return HealthCheckResponse(
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.environment,
            ready=ready,
            components=components,
        )

    async def _check_database(self) -> ComponentHealth:
        try:
            is_healthy: bool = await self._database_manager.ping()
        except Exception as exc:
            return ComponentHealth(name="database", status="unhealthy", detail=str(exc))

        if is_healthy:
            return ComponentHealth(name="database", status="healthy")
        return ComponentHealth(name="database", status="unhealthy", detail="Database is not initialized.")

    async def _check_redis(self) -> ComponentHealth:
        try:
            redis_client: Redis = self._redis_provider.get_client()
            await redis_client.ping()
        except Exception as exc:
            return ComponentHealth(name="redis", status="unhealthy", detail=str(exc))

        return ComponentHealth(name="redis", status="healthy")

    async def _check_comfyui(self) -> ComponentHealth:
        if self._comfy_client is None:
            return ComponentHealth(name="comfyui", status="unhealthy", detail="ComfyUI client is not initialized.")

        try:
            await self._comfy_client.ping()
        except Exception as exc:
            return ComponentHealth(name="comfyui", status="unhealthy", detail=str(exc))

        return ComponentHealth(name="comfyui", status="healthy")
