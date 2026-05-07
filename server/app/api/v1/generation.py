"""Generation routes backed by ComfyUI workflow execution."""

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.api.url_helpers import with_absolute_output_urls_for_job, with_absolute_output_urls_for_result
from app.comfy.exceptions import ComfyUIError, WorkflowTemplateError
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
    http_request: Request,
    request: WorkflowExecutionRequest = Body(default_factory=WorkflowExecutionRequest),
    execution_service: WorkflowExecutionService = Depends(get_workflow_execution_service),
) -> WorkflowExecutionResult:
    try:
        result: WorkflowExecutionResult = await execution_service.execute(request)
        return with_absolute_output_urls_for_result(result, http_request)
    except WorkflowTemplateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ComfyUIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/queue", response_model=QueueSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_workflow(
    request: WorkflowExecutionRequest = Body(default_factory=WorkflowExecutionRequest),
    queue_service: QueueService = Depends(get_queue_service),
) -> QueueSubmissionResponse:
    return await queue_service.submit(request)


@router.get("/jobs/{job_id}", response_model=TrackedJob)
async def get_job(
    http_request: Request,
    job_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> TrackedJob:
    job: TrackedJob | None = await queue_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return with_absolute_output_urls_for_job(job, http_request)


@router.post("/jobs/{job_id}/cancel", response_model=TrackedJob)
async def cancel_job(
    http_request: Request,
    job_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> TrackedJob:
    try:
        job: TrackedJob = await queue_service.cancel(job_id)
        return with_absolute_output_urls_for_job(job, http_request)
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
