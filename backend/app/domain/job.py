"""Modelo de dominio de un trabajo de análisis."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class JobStatus(str, Enum):
    """Estados posibles de un trabajo de análisis."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Indica si el trabajo ya no cambiará de estado."""
        return self in (JobStatus.COMPLETED, JobStatus.FAILED)


class LiftType(str, Enum):
    """Modalidades de levantamiento soportadas."""

    SNATCH = "snatch"


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    """Trabajo de análisis encolado para un vídeo concreto."""

    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    lift_type: LiftType = LiftType.SNATCH
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    detail: str | None = None

    def with_status(self, status: JobStatus, detail: str | None = None) -> AnalysisJob:
        """Devuelve una copia del trabajo con el estado actualizado."""
        return AnalysisJob(
            job_id=self.job_id,
            lift_type=self.lift_type,
            status=status,
            created_at=self.created_at,
            detail=detail if detail is not None else self.detail,
        )