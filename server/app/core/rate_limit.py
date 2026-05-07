"""Redis-backed API rate limiting middleware."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = request.app.state.settings
    if not settings.rate_limit_enabled or not request.url.path.startswith(settings.api_prefix):
        return await call_next(request)

    if request.url.path.startswith(f"{settings.api_prefix}/v1/health"):
        return await call_next(request)

    redis_provider = request.app.state.redis_provider
    redis_client: Redis = redis_provider.get_client()
    client_host: str = request.client.host if request.client is not None else "unknown"
    key: str = f"rate-limit:{client_host}:{request.url.path}"
    request_count: int = await redis_client.incr(key)
    if request_count == 1:
        await redis_client.expire(key, 60)

    if request_count > settings.rate_limit_requests_per_minute:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded."},
        )

    response: Response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(max(settings.rate_limit_requests_per_minute - request_count, 0))
    return response
