"""Health check routes for platform readiness and liveness."""

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_health_service
from app.schemas.health import HealthCheckResponse
from app.services.health import HealthService

router: APIRouter = APIRouter()


@router.get("", response_model=HealthCheckResponse)
async def health_check(
    response: Response,
    health_service: HealthService = Depends(get_health_service),
) -> HealthCheckResponse:
    health_response: HealthCheckResponse = await health_service.check()
    if not health_response.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health_response


@router.get("/live", response_model=HealthCheckResponse)
async def liveness_check(
    health_service: HealthService = Depends(get_health_service),
) -> HealthCheckResponse:
    return health_service.live()
