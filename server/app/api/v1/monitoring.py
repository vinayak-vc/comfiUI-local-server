"""Monitoring and dashboard endpoints."""

import aiofiles
from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request

from app.api.url_helpers import with_absolute_output_urls_for_jobs
from app.comfy.tracking import ComfyUIJobTracker
from app.core.config import Settings, get_settings
from app.dependencies import get_comfy_job_tracker, get_queue_service, require_admin_principal, require_principal
from app.queue.service import QueueService
from app.schemas.comfy import JobStatus, QueueMonitoringResponse
from app.schemas.monitoring import JobCountsResponse, JobListResponse, LogTailResponse

router: APIRouter = APIRouter(dependencies=[Depends(require_principal)])


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: JobStatus | None = Query(default=None),
    job_tracker: ComfyUIJobTracker = Depends(get_comfy_job_tracker),
) -> JobListResponse:
    jobs, total = await job_tracker.list_jobs(limit=limit, offset=offset, status=status)
    return JobListResponse(
        total=total,
        limit=limit,
        offset=offset,
        status=status,
        jobs=with_absolute_output_urls_for_jobs(jobs, request),
    )


@router.get("/queue", response_model=QueueMonitoringResponse)
async def queue_snapshot(
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueMonitoringResponse:
    return await queue_service.monitor()


@router.get("/jobs/counts", response_model=JobCountsResponse)
async def job_counts(
    job_tracker: ComfyUIJobTracker = Depends(get_comfy_job_tracker),
) -> JobCountsResponse:
    counts = await job_tracker.count_by_status()
    return JobCountsResponse(counts=counts)


async def _tail_lines(path: Path, lines: int) -> tuple[list[str], bool]:
    """
    Efficient-ish async tail implementation.

    Reads chunks from the end of the file until enough line breaks are found or a safety byte limit hits.
    """

    max_bytes: int = 2_000_000
    chunk_size: int = 4096

    file_size: int = path.stat().st_size
    if file_size == 0:
        return ([], False)

    # Read backwards in bounded chunks, keeping total buffer <= max_bytes.
    read_pos: int = file_size
    buf: bytes = b""
    bytes_read: int = 0

    while read_pos > 0 and len(buf.splitlines()) <= lines and bytes_read < max_bytes:
        read_size: int = min(chunk_size, read_pos, max_bytes - bytes_read)
        read_pos -= read_size
        bytes_read += read_size

        async with aiofiles.open(path, "rb") as f:
            await f.seek(read_pos)
            chunk: bytes = await f.read(read_size)

        buf = chunk + buf

        if read_pos == 0:
            break

    all_lines: list[str] = buf.decode("utf-8", errors="replace").splitlines()
    selected: list[str] = all_lines[-lines:] if lines > 0 else []
    truncated: bool = file_size > bytes_read and len(all_lines) > lines
    return (selected, truncated)


@router.get("/logs/tail", response_model=LogTailResponse)
async def logs_tail(
    lines: int = Query(default=200, ge=1, le=2000),
    settings: Settings = Depends(get_settings),
    _admin: object = Depends(require_admin_principal),
) -> LogTailResponse:
    log_path: Path = settings.log_file_path
    if not log_path.exists() or not log_path.is_file():
        return LogTailResponse(lines=[], truncated=False)

    try:
        result_lines, truncated = await _tail_lines(log_path, lines=lines)
        return LogTailResponse(lines=result_lines, truncated=truncated)
    except Exception:
        # Monitoring shouldn't break the entire API; return empty tail on unexpected issues.
        return LogTailResponse(lines=[], truncated=False)

