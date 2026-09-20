"""Consulta del estado de los trabajos encolados."""

from __future__ import annotations

from typing import Any, Protocol

from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.domain.job import JobStatus

# Correspondencia entre los estados de Celery y los del dominio.
CELERY_STATE_MAPPING: dict[str, JobStatus] = {
    "PENDING": JobStatus.PENDING,
    "RECEIVED": JobStatus.PENDING,
    "RETRY": JobStatus.PENDING,
    "STARTED": JobStatus.PROCESSING,
    "PROCESSING": JobStatus.PROCESSING,
    "SUCCESS": JobStatus.COMPLETED,
    "FAILURE": JobStatus.FAILED,
    "REVOKED": JobStatus.FAILED,
}


class JobState:
    """Instantánea del estado de un trabajo."""

    def __init__(
        self,
        status: JobStatus,
        result: dict[str, Any] | None = None,
        detail: str | None = None,
    ) -> None:
        """Crea la instantánea con el estado y los datos disponibles."""
        self.status = status
        self.result = result
        self.detail = detail


class JobRegistry(Protocol):
    """Contrato de cualquier registro consultable de trabajos."""

    def get_state(self, job_id: str) -> JobState:
        """Devuelve el estado actual del trabajo indicado."""
        ...


class CeleryJobRegistry:
    """Registro de trabajos respaldado por el backend de resultados de Celery."""

    def __init__(self, app: Any = celery_app) -> None:  # noqa: ANN401
        """Crea el registro sobre la aplicación Celery indicada."""
        self._app = app

    def get_state(self, job_id: str) -> JobState:
        """Traduce el estado de Celery al estado de dominio."""
        async_result = AsyncResult(job_id, app=self._app)
        status = CELERY_STATE_MAPPING.get(async_result.state, JobStatus.PENDING)

        if status is JobStatus.COMPLETED:
            return JobState(status=status, result=async_result.result)

        if status is JobStatus.FAILED:
            return JobState(status=status, detail=str(async_result.result))

        return JobState(status=status)