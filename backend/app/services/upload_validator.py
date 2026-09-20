"""Validación de los vídeos subidos por el usuario."""

from __future__ import annotations

from pathlib import Path


class InvalidUploadError(ValueError):
    """El fichero subido no cumple los requisitos del sistema."""


class UploadValidator:
    """Comprueba que un vídeo subido es aceptable para el análisis."""

    def __init__(self, allowed_extensions: tuple[str, ...], max_bytes: int) -> None:
        """Crea el validador con las restricciones indicadas."""
        self._allowed_extensions = allowed_extensions
        self._max_bytes = max_bytes

    def validate(self, filename: str | None, size_bytes: int) -> str:
        """Valida el fichero y devuelve su extensión normalizada.

        Raises:
            InvalidUploadError: Si el nombre, la extensión o el tamaño no son válidos.
        """
        if not filename:
            raise InvalidUploadError("El fichero subido no tiene nombre.")

        extension = Path(filename).suffix.lower()
        if extension not in self._allowed_extensions:
            permitidas = ", ".join(self._allowed_extensions)
            raise InvalidUploadError(
                f"Extensión no admitida: '{extension}'. Se admiten: {permitidas}."
            )

        if size_bytes <= 0:
            raise InvalidUploadError("El fichero subido está vacío.")

        if size_bytes > self._max_bytes:
            limite_mb = self._max_bytes / 1_048_576
            raise InvalidUploadError(f"El vídeo supera el límite de {limite_mb:.0f} MB.")

        return extension