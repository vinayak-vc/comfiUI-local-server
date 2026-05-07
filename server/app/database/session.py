"""SQLAlchemy async engine and session management."""

from collections.abc import AsyncIterator

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.database.base import Base
import app.models as models


class DatabaseSessionManager:
    """Owns SQLAlchemy engine and async session factory lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        if self._engine is not None:
            return

        self._ensure_sqlite_parent_directory()
        self._engine = create_async_engine(
            self._settings.database_url,
            echo=self._settings.database_echo,
            pool_pre_ping=self._settings.database_pool_pre_ping,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        if self._settings.database_auto_create_tables:
            await self.create_schema()

    async def close(self) -> None:
        if self._engine is None:
            return

        await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Database session factory has not been initialized.")

        async with self._session_factory() as session:
            yield session

    async def ping(self) -> bool:
        if self._engine is None:
            return False

        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    async def create_schema(self) -> None:
        if self._engine is None:
            raise RuntimeError("Database engine has not been initialized.")

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    def _ensure_sqlite_parent_directory(self) -> None:
        database_url: URL = make_url(self._settings.database_url)
        if database_url.drivername != "sqlite+aiosqlite":
            return

        database_path: str | None = database_url.database
        if database_path is None or database_path == ":memory:":
            return

        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
