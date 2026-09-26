"""Pruebas del traductor de estados de Celery."""

import pytest

from app.domain.job import JobStatus
from app.services.job_registry import CELERY_STATE_MAPPING


@pytest.mark.parametrize(
    ("celery_state", "expected"),
    [
        ("PENDING", JobStatus.PENDING),
        ("RECEIVED", JobStatus.PENDING),
        ("RETRY", JobStatus.PENDING),
        ("STARTED", JobStatus.PROCESSING),
        ("PROCESSING", JobStatus.PROCESSING),
        ("SUCCESS", JobStatus.COMPLETED),
        ("FAILURE", JobStatus.FAILED),
        ("REVOKED", JobStatus.FAILED),
    ],
)
def test_traduce_los_estados_de_celery(celery_state: str, expected: JobStatus) -> None:
    assert CELERY_STATE_MAPPING[celery_state] is expected


def test_un_estado_desconocido_se_considera_pendiente() -> None:
    assert CELERY_STATE_MAPPING.get("ESTADO_INVENTADO", JobStatus.PENDING) is JobStatus.PENDING
