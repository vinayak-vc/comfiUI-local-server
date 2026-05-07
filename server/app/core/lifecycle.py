"""Application lifespan orchestration."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.comfy.client import ComfyUIClient
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.redis import RedisClientProvider
from app.database.session import DatabaseSessionManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    configure_logging(settings)
    logger: structlog.stdlib.BoundLogger = structlog.get_logger("lifecycle")

    database_manager: DatabaseSessionManager = DatabaseSessionManager(settings)
    redis_provider: RedisClientProvider = RedisClientProvider(settings)
    comfy_client: ComfyUIClient = ComfyUIClient(settings)

    app.state.settings = settings
    app.state.database_manager = database_manager
    app.state.redis_provider = redis_provider
    app.state.comfy_client = comfy_client

    settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    settings.outputs_path.mkdir(parents=True, exist_ok=True)
    settings.workflows_path.mkdir(parents=True, exist_ok=True)

    await database_manager.connect()
    await redis_provider.connect()
    logger.info("application_started", environment=settings.environment)

    try:
        yield
    finally:
        await comfy_client.close()
        await redis_provider.close()
        await database_manager.close()
        logger.info("application_stopped")
