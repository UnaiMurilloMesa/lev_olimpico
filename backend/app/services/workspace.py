"""Gestión de los directorios de trabajo de cada análisis."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_NAME = "source"


class JobWorkspace:
    """Directorio aislado donde se procesa un trabajo concreto."""

    def __init__(self, root: Path, job_id: str) -> None:
        """Crea la representación del espacio de trabajo de un trabajo."""
        self._path = root / job_id
        self._job_id = job_id

    @property
    def path(self) -> Path:
        """Ruta del directorio de trabajo."""
        return self._path

    def create(self) -> Path:
        """Crea el directorio de trabajo si no existe."""
        self._path.mkdir(parents=True, exist_ok=True)
        return self._path

    def source_path(self, extension: str) -> Path:
        """Ruta donde se guarda el vídeo original subido."""
        return self._path / f"{UPLOAD_NAME}{extension}"

    def find_source(self) -> Path | None:
        """Localiza el vídeo original, sea cual sea su extensión."""
        matches = sorted(self._path.glob(f"{UPLOAD_NAME}.*"))
        return matches[0] if matches else None

    def result_path(self, name: str) -> Path:
        """Ruta de un artefacto generado por el análisis."""
        return self._path / name

    def exists(self) -> bool:
        """Indica si el directorio de trabajo existe."""
        return self._path.is_dir()

    def delete(self) -> None:
        """Elimina el directorio y todo su contenido."""
        shutil.rmtree(self._path, ignore_errors=True)
        logger.info("Espacio de trabajo eliminado: %s", self._job_id)