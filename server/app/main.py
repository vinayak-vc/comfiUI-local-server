"""FastAPI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from socketio import ASGIApp

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.lifecycle import lifespan
from app.core.logging import request_logging_middleware
from app.core.rate_limit import rate_limit_middleware
from app.socket.server import create_socketio_server


def create_app() -> FastAPI:
    settings: Settings = get_settings()
    app: FastAPI = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.middleware("http")(request_logging_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    app.mount(
        settings.upload_url_prefix,
        StaticFiles(directory=settings.uploads_path),
        name="uploads",
    )
    app.mount(
        settings.output_url_prefix,
        StaticFiles(directory=settings.outputs_path),
        name="outputs",
    )

    dashboard_dir: Path = Path(__file__).resolve().parent / "dashboard"
    if dashboard_dir.exists():
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(dashboard_dir), html=True),
            name="dashboard",
        )
    return app


app: FastAPI = create_app()
socket_app: ASGIApp = ASGIApp(
    create_socketio_server(get_settings()),
    other_asgi_app=app,
    socketio_path=get_settings().socketio_path,
)
