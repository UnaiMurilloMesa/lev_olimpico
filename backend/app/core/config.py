"""Configuración central de la aplicación."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes cargados desde variables de entorno o fichero .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Aplicación ---
    app_name: str = "Haltero Analyzer API"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Rutas ---
    base_dir: Path = Path(__file__).resolve().parents[2]
    models_dir: Path = base_dir / "models"
    storage_dir: Path = base_dir / "storage"
    pose_model_name: str = "pose_landmarker_heavy.task"

    # --- Límites de subida ---
    max_upload_bytes: int = 200 * 1024 * 1024
    allowed_video_extensions: tuple[str, ...] = (".mp4", ".mov", ".avi", ".mkv")

    # --- Cola ---
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    job_ttl_seconds: int = 60 * 30

    @property
    def pose_model_path(self) -> Path:
        """Ruta absoluta al modelo .task de MediaPipe."""
        return self.models_dir / self.pose_model_name


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia única de configuración."""
    return Settings()