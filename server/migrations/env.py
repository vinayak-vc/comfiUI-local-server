from __future__ import annotations

from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import your model's MetaData object here
from app.core.config import Settings
from app.database.base import Base

# Ensure models are imported so they are registered with SQLAlchemy metadata.
import app.models  # noqa: F401


# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url(database_url: str) -> str:
    # SQLAlchemy URL may be async-driver based (e.g. sqlite+aiosqlite, postgresql+asyncpg).
    # Alembic migrations typically run with a synchronous driver.
    return (
        database_url.replace("+aiosqlite", "")
        .replace("+asyncpg", "")
        .replace("+asyncmy", "")
        .replace("+aiomysql", "")
    )


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    # Examples:
    # - sqlite:///./data/app.db
    # - sqlite:////absolute/path/to/app.db
    if not database_url.startswith("sqlite:"):
        return

    # Strip scheme. Keep leading slashes behavior for absolute URLs.
    path_part = database_url.split("sqlite:", 1)[1]
    # For sqlite:///./data/app.db -> path_part == "///./data/app.db"
    # Normalize to a filesystem path.
    if path_part.startswith("///"):
        candidate = path_part[3:]
    elif path_part.startswith("//"):
        candidate = path_part[2:]
    elif path_part.startswith("/"):
        candidate = path_part[1:]
    else:
        candidate = path_part

    db_path = Path(candidate)
    if db_path.parent and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)


def _get_settings() -> Settings:
    # Settings reads from environment and optional .env automatically.
    return Settings()


def run_migrations_offline() -> None:
    settings = _get_settings()
    database_url = _sync_database_url(settings.database_url)
    _ensure_sqlite_parent_dir(database_url)

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = _get_settings()
    database_url = _sync_database_url(settings.database_url)
    _ensure_sqlite_parent_dir(database_url)

    # Create a synchronous engine for migrations.
    connectable = engine_from_config(
        {"sqlalchemy.url": database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

