"""Generation routes backed by ComfyUI workflow execution."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.comfy.exceptions import ComfyUIError
from app.dependencies import get_queue_service, get_workflow_execution_service, require_principal
from app.queue.service import QueueService
from app.schemas.comfy import (
    QueueMonitoringResponse,
    QueueSubmissionResponse,
    TrackedJob,
    WorkflowExecutionRequest,
    WorkflowExecutionResult,
)
from app.services.workflow_execution import WorkflowExecutionService

router: APIRouter = APIRouter(dependencies=[Depends(require_principal)])


@router.post("/execute", response_model=WorkflowExecutionResult)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    execution_service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionResult:
    try:
        return await execution_service.execute(request)
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/queue", response_model=QueueSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_workflow(
    request: WorkflowExecutionRequest,
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueSubmissionResponse:
    return await queue_service.submit(request)


@router.get("/jobs/{job_id}", response_model=TrackedJob)
async def get_job(
    job_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> TrackedJob:
    job: TrackedJob | None = await queue_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return job


@router.post("/jobs/{job_id}/cancel", response_model=TrackedJob)
async def cancel_job(
    job_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> TrackedJob:
    try:
        return await queue_service.cancel(job_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        ) from exc
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/queue", response_model=QueueMonitoringResponse)
async def monitor_queue(
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueMonitoringResponse:
    return await queue_service.monitor()
