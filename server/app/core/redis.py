"""Redis connection management for infrastructure services."""

from redis.asyncio import Redis

from app.core.config import Settings


class RedisClientProvider:
    """Owns the application Redis client lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        self._client: Redis | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return

        self._client = Redis.from_url(
            self._settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=self._settings.redis_socket_timeout_seconds,
        )
        await self._client.ping()

    async def close(self) -> None:
        if self._client is None:
            return

        await self._client.aclose()
        self._client = None

    def get_client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis client has not been initialized.")
        return self._client
