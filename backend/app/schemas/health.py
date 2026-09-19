"""Esquemas de entrada/salida de los endpoints de salud."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""

    status: str = Field(description="Estado general del servicio.")
    version: str = Field(description="Versión de la API.")
    pose_model_available: bool = Field(
        description="Indica si el modelo de MediaPipe está presente en disco."
    )