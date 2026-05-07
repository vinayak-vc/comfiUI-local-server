"""Structured logging setup and request logging middleware."""

import logging
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import structlog
from fastapi import Request, Response
from structlog.typing import EventDict, Processor

from app.core.config import Settings


def add_log_level(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    event_dict["level"] = method_name.upper()
    return event_dict


def configure_logging(settings: Settings) -> None:
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    log_file_path: Path = settings.log_file_path
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger: logging.Logger = logging.getLogger()
    file_handler_name: str = f"structured-file:{log_file_path.resolve()}"
    has_file_handler: bool = any(handler.get_name() == file_handler_name for handler in root_logger.handlers)
    if not has_file_handler:
        file_handler: logging.FileHandler = logging.FileHandler(
            filename=log_file_path,
            encoding="utf-8",
        )
        file_handler.set_name(file_handler_name)
        file_handler.setLevel(settings.log_level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(file_handler)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger("request")
    start_time: float = time.perf_counter()

    try:
        response: Response = await call_next(request)
    except Exception:
        elapsed_ms: float = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "request_failed",
            method=request.method,
            path=request.url.path,
            elapsed_ms=round(elapsed_ms, 2),
        )
        raise

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        elapsed_ms=round(elapsed_ms, 2),
    )
    return response
