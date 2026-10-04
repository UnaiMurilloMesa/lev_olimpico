"""Instancia de Celery para el procesamiento asíncrono de análisis."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "snatch_analyzer",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Madrid",
    enable_utc=True,
    result_expires=settings.job_ttl_seconds,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery_app.conf.beat_schedule = {
    "limpieza-de-espacios-caducados": {
        "task": "tasks.cleanup_workspaces",
        "schedule": float(settings.cleanup_interval_seconds),
    },
}
