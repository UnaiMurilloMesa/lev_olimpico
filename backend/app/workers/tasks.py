"""Tareas asíncronas ejecutadas por los workers de Celery."""

from app.core.celery_app import celery_app


@celery_app.task(name="tasks.ping")
def ping() -> str:
    """Tarea trivial para verificar que el worker responde."""
    return "pong"
