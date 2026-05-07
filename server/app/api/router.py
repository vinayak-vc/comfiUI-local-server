"""Top-level API router composition."""

from fastapi import APIRouter

from app.api.v1.router import api_router as api_v1_router

api_router: APIRouter = APIRouter()
api_router.include_router(api_v1_router, prefix="/v1")
