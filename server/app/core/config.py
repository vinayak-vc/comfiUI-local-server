"""Environment-driven application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ComfyUI Orchestration Platform"
    app_version: str = "0.1.0"
    environment: Literal["local", "development", "staging", "production"] = "local"
    debug: bool = False
    api_prefix: str = "/api"
    cors_allowed_origins: list[str] = Field(default_factory=list)

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    database_echo: bool = False
    database_pool_pre_ping: bool = True

    redis_url: str = "redis://localhost:6379/0"
    redis_socket_timeout_seconds: float = 5.0

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = True
    log_file_path: Path = Path("logs/app.log")

    uploads_path: Path = Path("uploads")
    outputs_path: Path = Path("outputs")
    workflows_path: Path = Path("workflows")
    max_upload_size_bytes: int = 104857600
    allowed_upload_extensions: list[str] = Field(
        default_factory=lambda: [
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".gif",
            ".mp4",
            ".webm",
            ".mov",
        ]
    )
    upload_url_prefix: str = "/uploads"
    storage_cleanup_after_days: int = 30
    database_auto_create_tables: bool = True

    comfyui_base_url: str = "http://localhost:8188"
    comfyui_ws_url: str = "ws://localhost:8188/ws"
    comfyui_request_timeout_seconds: float = 30.0
    comfyui_execution_timeout_seconds: float = 1800.0
    comfyui_poll_interval_seconds: float = 1.0
    comfyui_job_ttl_seconds: int = 86400
    output_url_prefix: str = "/outputs"

    celery_broker_url: str | None = None
    celery_result_backend_url: str | None = None
    celery_queue_name: str = "gpu_render_queue"
    celery_worker_concurrency: int = 1
    celery_task_soft_time_limit_seconds: int = 1800
    celery_task_time_limit_seconds: int = 1860
    celery_task_max_retries: int = 2
    celery_task_retry_delay_seconds: int = 30

    socketio_path: str = "socket.io"
    socketio_channel: str = "socketio"
    socketio_allowed_origins: list[str] = Field(default_factory=list)
    socketio_preview_encoding: Literal["base64"] = "base64"

    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    allow_user_registration: bool = True
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 120
    api_key_header_name: str = "X-API-Key"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def resolved_celery_broker_url(self) -> str:
        if self.celery_broker_url is not None:
            return self.celery_broker_url
        return self.redis_url

    @property
    def resolved_celery_result_backend_url(self) -> str:
        if self.celery_result_backend_url is not None:
            return self.celery_result_backend_url
        return self.redis_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
