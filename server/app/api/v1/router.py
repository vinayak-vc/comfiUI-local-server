"""Version 1 API router composition."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.generation import router as generation_router
from app.api.v1.health import router as health_router
from app.api.v1.storage import router as storage_router

api_router: APIRouter = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(generation_router, prefix="/generation", tags=["generation"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(storage_router, prefix="/storage", tags=["storage"])
