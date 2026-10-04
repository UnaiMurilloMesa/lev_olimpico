"""Esquemas de entrada/salida de los endpoints de análisis."""

from pydantic import BaseModel, Field

from app.domain.job import JobStatus, LiftType


class AnalysisCreatedResponse(BaseModel):
    """Respuesta a la creación de un trabajo de análisis."""

    job_id: str = Field(description="Identificador único del trabajo encolado.")
    status: JobStatus = Field(description="Estado inicial del trabajo.")
    lift_type: LiftType = Field(description="Modalidad de levantamiento analizada.")


class PhaseSummary(BaseModel):
    """Resumen de una fase del levantamiento."""

    phase: str = Field(description="Identificador de la fase.")
    label: str = Field(description="Nombre legible de la fase.")
    start_seconds: float = Field(description="Inicio de la fase desde el despegue.")
    end_seconds: float = Field(description="Fin de la fase desde el despegue.")
    duration_seconds: float = Field(description="Duración de la fase.")
    snapshot: str | None = Field(default=None, description="Nombre de la captura asociada.")


class AnalysisSummary(BaseModel):
    """Datos del análisis una vez completado."""

    video_name: str = Field(description="Nombre del fichero de vídeo generado.")
    processed_frames: int = Field(description="Fotogramas procesados del vídeo.")
    detected_frames: int = Field(description="Fotogramas con pose detectada.")
    detection_ratio: float = Field(
        description="Proporción de puntos clave rastreados con alta confianza."
    )
    interpolated_frames: int = Field(
        description="Fotogramas cuya pose se reconstruyó por interpolación."
    )
    duration_seconds: float = Field(description="Duración del vídeo analizado.")
    bar_path_deviation: float = Field(description="Desviación horizontal relativa de la barra.")
    bar_path_quality: str = Field(description="Valoración de la verticalidad de la trayectoria.")
    lift_start_seconds: float = Field(description="Instante de despegue de la barra.")
    lift_end_seconds: float = Field(description="Instante en que termina el levantamiento.")
    lift_duration_seconds: float = Field(description="Duración del levantamiento acotado.")
    peak_velocity_ms: float = Field(description="Velocidad vertical máxima de la barra.")
    peak_velocity_time: float = Field(description="Instante de la velocidad máxima.")
    has_velocity_chart: bool = Field(description="Indica si hay gráfica de velocidad.")
    phases: list[PhaseSummary] = Field(
        default_factory=list, description="División del levantamiento en fases."
    )


class AnalysisStatusResponse(BaseModel):
    """Estado actual de un trabajo de análisis."""

    job_id: str = Field(description="Identificador del trabajo consultado.")
    status: JobStatus = Field(description="Estado actual del trabajo.")
    detail: str | None = Field(default=None, description="Mensaje de error si el trabajo falló.")
    result: AnalysisSummary | None = Field(
        default=None, description="Resumen disponible solo cuando el trabajo ha terminado bien."
    )