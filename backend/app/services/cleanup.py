"""Eliminación de los espacios de trabajo caducados."""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CleanupReport:
    """Resumen de una pasada de limpieza."""

    inspected: int
    removed: int
    freed_bytes: int

    @property
    def freed_megabytes(self) -> float:
        """Espacio liberado, en megabytes."""
        return round(self.freed_bytes / 1_048_576, 2)


class WorkspaceCleaner:
    """Borra los espacios de trabajo que superan la antigüedad admitida.

    El sistema no conserva vídeos ni resultados más allá del tiempo necesario
    para que el usuario los consulte; esta limpieza garantiza que nada quede
    almacenado de forma indefinida aunque el cliente no llame al borrado.
    """

    def __init__(self, storage_dir: Path, max_age_seconds: int) -> None:
        """Crea el limpiador sobre el directorio de almacenamiento indicado."""
        self._storage_dir = storage_dir
        self._max_age_seconds = max_age_seconds

    def clean(self, now: float | None = None) -> CleanupReport:
        """Elimina los directorios caducados y devuelve el resumen.

        Args:
            now: Instante de referencia, inyectable para poder probarlo.
        """
        reference = now if now is not None else time.time()
        if not self._storage_dir.is_dir():
            return CleanupReport(inspected=0, removed=0, freed_bytes=0)

        inspected = 0
        removed = 0
        freed = 0

        for workspace in self._storage_dir.iterdir():
            if not workspace.is_dir():
                continue

            inspected += 1
            if not self._is_expired(workspace, reference):
                continue

            size = _directory_size(workspace)
            shutil.rmtree(workspace, ignore_errors=True)
            if not workspace.exists():
                removed += 1
                freed += size
                logger.info("Espacio de trabajo caducado eliminado: %s", workspace.name)

        return CleanupReport(inspected=inspected, removed=removed, freed_bytes=freed)

    def _is_expired(self, workspace: Path, reference: float) -> bool:
        """Indica si un directorio supera la antigüedad admitida.

        Se usa la modificación más reciente de su contenido, no la del propio
        directorio: así un análisis que todavía se está escribiendo nunca se
        considera caducado.
        """
        latest = _latest_modification(workspace)
        return reference - latest > self._max_age_seconds


def _latest_modification(directory: Path) -> float:
    """Marca de tiempo más reciente dentro de un directorio."""
    times = [directory.stat().st_mtime]
    times.extend(item.stat().st_mtime for item in directory.rglob("*") if item.is_file())
    return max(times)


def _directory_size(directory: Path) -> int:
    """Tamaño total en bytes del contenido de un directorio."""
    return sum(item.stat().st_size for item in directory.rglob("*") if item.is_file())