"""Tareas asíncronas ejecutadas por los workers de Celery."""

from __future__ import annotations

import logging
from typing import Any

from celery import Task

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.domain.job import JobStatus
from app.services.cleanup import WorkspaceCleaner
from app.services.factory import build_analysis_service
from app.services.workspace import JobWorkspace

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.ping")
def ping() -> str:
    """Tarea trivial para verificar que el worker responde."""
    return "pong"


@celery_app.task(name="tasks.analyze_lift", bind=True)
def analyze_lift(
    self: Task,
    job_id: str,
    start_seconds: float = 0.0,
    athlete_height_m: float = 1.75,
) -> dict[str, Any]:
    """Ejecuta el análisis del vídeo asociado a un trabajo.

    Returns:
        Resumen del análisis serializable a JSON.

    Raises:
        FileNotFoundError: Si no se encuentra el vídeo original del trabajo.
    """
    settings = get_settings()
    workspace = JobWorkspace(settings.storage_dir, job_id)

    source = workspace.find_source()
    if source is None:
        raise FileNotFoundError(f"No se encontró el vídeo original del trabajo {job_id}")

    self.update_state(state=JobStatus.PROCESSING.value.upper())
    logger.info("Analizando el trabajo %s", job_id)

    service = build_analysis_service(settings)
    result = service.analyze(source, workspace.path, start_seconds, athlete_height_m)
    source.unlink(missing_ok=True)

    return {
        "job_id": job_id,
        "video_name": result.video_path.name,
        "processed_frames": result.processed_frames,
        "detected_frames": result.detected_frames,
        "detection_ratio": round(result.detection_ratio, 4),
        "interpolated_frames": result.interpolated_frames,
        "duration_seconds": round(result.duration_seconds, 2),
        "bar_path_deviation": result.bar_path_deviation,
        "bar_path_quality": result.bar_path_quality,
        "lift_start_seconds": result.lift_start_seconds,
        "lift_end_seconds": result.lift_end_seconds,
        "lift_duration_seconds": result.lift_duration_seconds,
        "peak_velocity_ms": result.peak_velocity_ms,
        "peak_velocity_time": result.peak_velocity_time,
        "has_velocity_chart": result.velocity_chart is not None,
        "overall_score": result.overall_score,
        "phases": [
            {
                "phase": phase.phase,
                "label": phase.label,
                "start_seconds": phase.start_seconds,
                "end_seconds": phase.end_seconds,
                "duration_seconds": phase.duration_seconds,
                "snapshot": phase.snapshot,
                "score": phase.score,
                "level": phase.level,
                "criteria": [
                    {
                        "criterion": item.criterion,
                        "score": item.score,
                        "level": item.level,
                        "measured_value": item.measured_value,
                        "explanation": item.explanation,
                    }
                    for item in phase.criteria
                ],
            }
            for phase in result.phases
        ],
    }


@celery_app.task(name="tasks.cleanup_workspaces")
def cleanup_workspaces() -> dict[str, Any]:
    """Elimina los espacios de trabajo que han superado su tiempo de vida."""
    settings = get_settings()
    cleaner = WorkspaceCleaner(settings.storage_dir, settings.workspace_max_age_seconds)
    report = cleaner.clean()

    if report.removed:
        logger.info(
            "Limpieza: %d espacios eliminados, %.2f MB liberados",
            report.removed,
            report.freed_megabytes,
        )

    return {
        "inspected": report.inspected,
        "removed": report.removed,
        "freed_megabytes": report.freed_megabytes,
    }