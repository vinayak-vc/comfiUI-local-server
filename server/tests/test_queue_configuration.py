"""Celery queue configuration tests."""

from app.core.config import Settings
from app.queue.celery_app import celery_app
from app.queue.tasks import render_workflow_task


def test_celery_uses_single_gpu_queue_configuration() -> None:
    settings: Settings = Settings()

    assert celery_app.conf.task_default_queue == settings.celery_queue_name
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.worker_concurrency == settings.celery_worker_concurrency
    assert settings.celery_worker_concurrency == 1
    assert render_workflow_task.name in celery_app.tasks
