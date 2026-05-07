"""Client-facing URL shaping tests."""

from datetime import UTC, datetime

from starlette.requests import Request

from app.api.url_helpers import with_absolute_output_urls_for_job, with_absolute_output_urls_for_result
from app.schemas.comfy import GenerationMode, JobStatus, OutputAsset, TrackedJob, WorkflowExecutionResult


def test_execution_result_output_urls_are_absolute_without_mutating_source() -> None:
    request: Request = _request("192.168.1.28:8000")
    output: OutputAsset = OutputAsset(
        filename="ComfyUI_00007_.png",
        subfolder="",
        type="output",
        url="/outputs/ComfyUI_00007_.png",
        media_type="image",
    )
    result: WorkflowExecutionResult = WorkflowExecutionResult(
        job_id="job-id",
        prompt_id="prompt-id",
        status=JobStatus.COMPLETED,
        outputs=[output],
        events=[],
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )

    updated_result: WorkflowExecutionResult = with_absolute_output_urls_for_result(result, request)

    assert updated_result.outputs[0].url == "http://192.168.1.28:8000/outputs/ComfyUI_00007_.png"
    assert result.outputs[0].url == "/outputs/ComfyUI_00007_.png"


def test_tracked_job_output_urls_keep_existing_absolute_urls() -> None:
    request: Request = _request("localhost:8000")
    job: TrackedJob = TrackedJob(
        job_id="job-id",
        mode=GenerationMode.TEXT_TO_IMAGE,
        status=JobStatus.COMPLETED,
        outputs=[
            OutputAsset(
                filename="image.png",
                subfolder="",
                type="output",
                url="https://cdn.example.com/image.png",
                media_type="image",
            )
        ],
    )

    updated_job: TrackedJob = with_absolute_output_urls_for_job(job, request)

    assert updated_job.outputs[0].url == "https://cdn.example.com/image.png"


def _request(host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/generation/execute",
            "headers": [(b"host", host.encode("ascii"))],
            "scheme": "http",
            "server": (host.split(":")[0], int(host.split(":")[1])),
        }
    )
