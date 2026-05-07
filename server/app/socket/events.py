"""Socket.IO event names and room helpers."""

from enum import StrEnum


class SocketEvent(StrEnum):
    CONNECTED = "connected"
    SUBSCRIBE_JOB = "subscribe_job"
    UNSUBSCRIBE_JOB = "unsubscribe_job"
    SUBSCRIPTION_READY = "subscription_ready"
    SUBSCRIPTION_ERROR = "subscription_error"
    JOB_QUEUED = "job_queued"
    JOB_STARTED = "job_started"
    PROGRESS_UPDATE = "progress_update"
    PREVIEW_IMAGE = "preview_image"
    PREVIEW_VIDEO = "preview_video"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"


def job_room(job_id: str) -> str:
    return f"job:{job_id}"
