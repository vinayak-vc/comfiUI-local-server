"""Startup import tests for the FastAPI application factory."""

from fastapi import FastAPI

from app.main import create_app


def test_create_app_returns_fastapi_instance() -> None:
    app: FastAPI = create_app()

    assert isinstance(app, FastAPI)
