"""Endpoints de creación y consulta de análisis de levantamientos."""

from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import JobRegistryDep, SettingsDep, UploadValidatorDep
from app.domain.job import AnalysisJob, JobStatus, LiftType
from app.schemas.analysis import (
    AnalysisCreatedResponse,
    AnalysisStatusResponse,
    AnalysisSummary,
)
from app.services.upload_validator import InvalidUploadError
from app.services.workspace import JobWorkspace
from app.workers.tasks import analyze_lift

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyses", tags=["analyses"])

RESULT_VIDEO_NAME = "analysis.mp4"
CHART_IMAGE_NAME = "velocity.png"


@router.post(
    "",
    response_model=AnalysisCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis(
    settings: SettingsDep,
    validator: UploadValidatorDep,
    video: UploadFile = File(description="Vídeo del levantamiento."),
    lift_type: LiftType = Form(default=LiftType.SNATCH),
    start_seconds: float = Form(default=0.0, ge=0.0),
    athlete_height_m: float = Form(default=1.75, gt=1.0, lt=2.5),
) -> AnalysisCreatedResponse:
    """Encola el análisis de un vídeo de levantamiento.

    Raises:
        HTTPException: Si el vídeo no supera la validación.
    """
    try:
        extension = validator.validate(video.filename, video.size or 0)
    except InvalidUploadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error

    job = AnalysisJob(lift_type=lift_type)
    workspace = JobWorkspace(settings.storage_dir, job.job_id)
    workspace.create()

    destination = workspace.source_path(extension)
    with destination.open("wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    analyze_lift.apply_async(args=[job.job_id, start_seconds, athlete_height_m], task_id=job.job_id)
    logger.info("Trabajo %s encolado (%s)", job.job_id, lift_type.value)

    return AnalysisCreatedResponse(
        job_id=job.job_id, status=JobStatus.PENDING, lift_type=lift_type
    )


@router.get("/{job_id}", response_model=AnalysisStatusResponse)
def get_analysis_status(job_id: str, registry: JobRegistryDep) -> AnalysisStatusResponse:
    """Consulta el estado de un trabajo de análisis."""
    state = registry.get_state(job_id)
    summary = AnalysisSummary(**state.result) if state.result else None

    return AnalysisStatusResponse(
        job_id=job_id, status=state.status, detail=state.detail, result=summary
    )


@router.get("/{job_id}/video", response_class=FileResponse)
def download_analysis_video(job_id: str, settings: SettingsDep) -> FileResponse:
    """Devuelve el vídeo analizado de un trabajo completado.

    Raises:
        HTTPException: Si el vídeo todavía no existe.
    """
    workspace = JobWorkspace(settings.storage_dir, job_id)
    video_path = workspace.result_path(RESULT_VIDEO_NAME)

    if not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El vídeo analizado no está disponible para este trabajo.",
        )

    return FileResponse(path=video_path, media_type="video/mp4", filename=RESULT_VIDEO_NAME)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(job_id: str, settings: SettingsDep) -> None:
    """Elimina todos los datos asociados a un análisis."""
    JobWorkspace(settings.storage_dir, job_id).delete()
    logger.info("Trabajo %s eliminado a petición del cliente", job_id)

@router.get("/{job_id}/velocity-chart", response_class=FileResponse)
def download_velocity_chart(job_id: str, settings: SettingsDep) -> FileResponse:
    """Devuelve la gráfica de velocidad de un trabajo completado.

    Raises:
        HTTPException: Si la gráfica todavía no existe.
    """
    chart_path = JobWorkspace(settings.storage_dir, job_id).result_path(CHART_IMAGE_NAME)

    if not chart_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La gráfica de velocidad no está disponible para este trabajo.",
        )

    return FileResponse(path=chart_path, media_type="image/png", filename=CHART_IMAGE_NAME)