"""Endpoints de salud y diagnóstico."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Comprueba que la API está viva y que el modelo de pose está disponible."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        pose_model_available=settings.pose_model_path.is_file(),
    )
