"""Dependencias inyectables de la capa de API."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.job_registry import CeleryJobRegistry, JobRegistry
from app.services.upload_validator import UploadValidator

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_upload_validator(settings: SettingsDep) -> UploadValidator:
    """Construye el validador de subidas con los límites configurados."""
    return UploadValidator(
        allowed_extensions=settings.allowed_video_extensions,
        max_bytes=settings.max_upload_bytes,
    )


def get_job_registry() -> JobRegistry:
    """Construye el registro de trabajos respaldado por Celery."""
    return CeleryJobRegistry()


UploadValidatorDep = Annotated[UploadValidator, Depends(get_upload_validator)]
JobRegistryDep = Annotated[JobRegistry, Depends(get_job_registry)]