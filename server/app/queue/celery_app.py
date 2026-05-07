"""Celery application configured for FIFO GPU-safe workflow execution."""

from celery import Celery
from kombu import Queue

from app.core.config import Settings, get_settings


def create_celery_app() -> Celery:
    settings: Settings = get_settings()
    celery_app: Celery = Celery(
        "comfyui_orchestrator",
        broker=settings.resolved_celery_broker_url,
        backend=settings.resolved_celery_result_backend_url,
        include=["app.queue.tasks"],
    )
    celery_app.conf.update(
        broker_connection_retry_on_startup=True,
        task_default_queue=settings.celery_queue_name,
        task_queues=[Queue(settings.celery_queue_name, routing_key=settings.celery_queue_name)],
        task_default_exchange=settings.celery_queue_name,
        task_default_routing_key=settings.celery_queue_name,
        task_routes={
            "app.queue.tasks.render_workflow": {
                "queue": settings.celery_queue_name,
                "routing_key": settings.celery_queue_name,
            },
        },
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_prefetch_multiplier=1,
        worker_concurrency=settings.celery_worker_concurrency,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        task_time_limit=settings.celery_task_time_limit_seconds,
        task_soft_time_limit=settings.celery_task_soft_time_limit_seconds,
        broker_transport_options={
            "visibility_timeout": settings.celery_task_time_limit_seconds,
            "queue_order_strategy": "sorted",
        },
        result_expires=settings.comfyui_job_ttl_seconds,
    )
    return celery_app


celery_app: Celery = create_celery_app()
