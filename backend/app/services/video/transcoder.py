"""Transcodificación de vídeo a un formato compatible con Android."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT_SECONDS = 600


class TranscodingError(RuntimeError):
    """Error durante la conversión de un vídeo."""


class VideoTranscoder(Protocol):
    """Contrato de cualquier conversor de vídeo."""

    def to_android_compatible(self, source: Path, destination: Path) -> Path:
        """Convierte un vídeo a un formato reproducible en Android."""
        ...


class FfmpegTranscoder:
    """Conversor basado en el binario de ffmpeg."""

    def __init__(self, binary: str = "ffmpeg", crf: int = 23, preset: str = "medium") -> None:
        """Crea el conversor con los parámetros de calidad indicados."""
        self._binary = binary
        self._crf = crf
        self._preset = preset

    @property
    def is_available(self) -> bool:
        """Indica si el binario de ffmpeg está disponible en el sistema."""
        return shutil.which(self._binary) is not None

    def to_android_compatible(self, source: Path, destination: Path) -> Path:
        """Convierte el vídeo a H.264 + yuv420p con el índice al inicio.

        Raises:
            TranscodingError: Si ffmpeg no está disponible o la conversión falla.
        """
        if not self.is_available:
            raise TranscodingError(f"No se encontró el binario '{self._binary}' en el sistema.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        command = self._build_command(source, destination)

        try:
            result = subprocess.run(  # noqa: S603
                command,
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise TranscodingError(f"ffmpeg superó el tiempo límite con {source}") from error

        if result.returncode != 0:
            logger.error("ffmpeg falló: %s", result.stderr[-2000:])
            raise TranscodingError(f"ffmpeg devolvió el código {result.returncode}")

        logger.info("Vídeo transcodificado a %s", destination)
        return destination

    def _build_command(self, source: Path, destination: Path) -> list[str]:
        """Construye la invocación de ffmpeg."""
        return [
            self._binary,
            "-y",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            self._preset,
            "-crf",
            str(self._crf),
            # Obligatorio: los decodificadores hardware de Android solo
            # admiten submuestreo de croma 4:2:0.
            "-pix_fmt",
            "yuv420p",
            # Mueve el índice al principio para permitir reproducción progresiva.
            "-movflags",
            "+faststart",
            # El análisis no necesita audio y así evitamos incompatibilidades.
            "-an",
            str(destination),
        ]