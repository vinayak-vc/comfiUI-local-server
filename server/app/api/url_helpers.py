"""Helpers for shaping API URLs for client-facing responses."""

from urllib.parse import urljoin, urlsplit

from fastapi import Request

from app.schemas.comfy import OutputAsset, TrackedJob, WorkflowExecutionResult


def with_absolute_output_urls_for_result(
    result: WorkflowExecutionResult,
    request: Request,
) -> WorkflowExecutionResult:
    """Returns an execution result with output URLs resolved against the request host."""

    updated_result: WorkflowExecutionResult = result.model_copy(deep=True)
    updated_result.outputs = [_with_absolute_output_url(output, request) for output in result.outputs]
    return updated_result


def with_absolute_output_urls_for_job(job: TrackedJob, request: Request) -> TrackedJob:
    """Returns a tracked job with output URLs resolved against the request host."""

    updated_job: TrackedJob = job.model_copy(deep=True)
    updated_job.outputs = [_with_absolute_output_url(output, request) for output in job.outputs]
    return updated_job


def with_absolute_output_urls_for_jobs(jobs: list[TrackedJob], request: Request) -> list[TrackedJob]:
    """Returns tracked jobs with output URLs resolved against the request host."""

    return [with_absolute_output_urls_for_job(job, request) for job in jobs]


def _with_absolute_output_url(output: OutputAsset, request: Request) -> OutputAsset:
    if _is_absolute_url(str(output.url)):
        return output

    updated_output: OutputAsset = output.model_copy()
    updated_output.url = urljoin(str(request.base_url), str(output.url).lstrip("/"))
    return updated_output


def _is_absolute_url(url: str) -> bool:
    parsed = urlsplit(url)
    return bool(parsed.scheme and parsed.netloc)
