"""Pruebas del modelo de dominio de trabajos de análisis."""

from app.domain.job import AnalysisJob, JobStatus, LiftType


def test_un_trabajo_nuevo_esta_pendiente() -> None:
    job = AnalysisJob()

    assert job.status is JobStatus.PENDING
    assert job.lift_type is LiftType.SNATCH


def test_cada_trabajo_recibe_un_identificador_distinto() -> None:
    assert AnalysisJob().job_id != AnalysisJob().job_id


def test_actualizar_el_estado_conserva_el_identificador() -> None:
    job = AnalysisJob()

    actualizado = job.with_status(JobStatus.PROCESSING)

    assert actualizado.job_id == job.job_id
    assert actualizado.status is JobStatus.PROCESSING


def test_los_estados_finales_se_identifican_correctamente() -> None:
    assert JobStatus.COMPLETED.is_terminal is True
    assert JobStatus.FAILED.is_terminal is True
    assert JobStatus.PENDING.is_terminal is False
    assert JobStatus.PROCESSING.is_terminal is False


def test_el_fallo_puede_llevar_un_detalle() -> None:
    job = AnalysisJob().with_status(JobStatus.FAILED, detail="vídeo corrupto")

    assert job.detail == "vídeo corrupto"
