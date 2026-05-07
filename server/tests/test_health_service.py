"""Health service unit tests."""

import pytest

from app.core.config import Settings
from app.schemas.health import HealthCheckResponse
from app.services.health import HealthService


pytestmark = pytest.mark.asyncio


class UninitializedDatabaseManager:
    async def ping(self) -> bool:
        return False


class UninitializedRedisProvider:
    def get_client(self) -> object:
        raise RuntimeError("Redis client has not been initialized.")


async def test_health_service_reports_unready_for_missing_infrastructure() -> None:
    settings: Settings = Settings()
    service: HealthService = HealthService(
        settings=settings,
        database_manager=UninitializedDatabaseManager(),
        redis_provider=UninitializedRedisProvider(),
    )

    response: HealthCheckResponse = await service.check()

    assert response.ready is False
    assert len(response.components) == 3
