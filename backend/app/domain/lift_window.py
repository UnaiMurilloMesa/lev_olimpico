"""Acotación temporal del tramo útil de un levantamiento."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.sequence import PoseSequence


class InvalidLiftWindowError(ValueError):
    """La ventana solicitada no es válida para la secuencia dada."""


@dataclass(frozen=True, slots=True)
class LiftWindow:
    """Tramo de fotogramas que abarca el levantamiento.

    Los índices se refieren a la secuencia analizada, no al vídeo original:
    tras el submuestreo ambos pueden no coincidir.
    """

    start_index: int
    end_index: int

    def __post_init__(self) -> None:
        """Valida que la ventana esté bien formada.

        Raises:
            InvalidLiftWindowError: Si los índices son negativos o están invertidos.
        """
        if self.start_index < 0:
            raise InvalidLiftWindowError("El inicio de la ventana no puede ser negativo.")
        if self.end_index < self.start_index:
            raise InvalidLiftWindowError("El fin de la ventana precede a su inicio.")

    def __len__(self) -> int:
        """Número de fotogramas que abarca la ventana."""
        return self.end_index - self.start_index + 1

    def contains(self, frame_index: int) -> bool:
        """Indica si un fotograma cae dentro de la ventana."""
        return self.start_index <= frame_index <= self.end_index

    def duration_seconds(self, fps: float) -> float:
        """Duración de la ventana en segundos."""
        return len(self) / fps if fps else 0.0

    @classmethod
    def from_seconds(
        cls, start_seconds: float, sequence: PoseSequence, end_seconds: float | None = None
    ) -> LiftWindow:
        """Construye la ventana a partir de instantes en segundos.

        El instante final, si se omite, es el último fotograma de la secuencia.

        Raises:
            InvalidLiftWindowError: Si la secuencia está vacía o el inicio queda fuera.
        """
        if not sequence.frames:
            raise InvalidLiftWindowError("No se puede acotar una secuencia vacía.")

        last_index = len(sequence) - 1
        start_index = round(start_seconds * sequence.fps)
        if start_index > last_index:
            raise InvalidLiftWindowError(
                f"El inicio ({start_seconds:.2f}s) excede la duración del vídeo."
            )

        end_index = (
            last_index if end_seconds is None else min(round(
                end_seconds * sequence.fps), last_index)
        )
        return cls(start_index=max(0, start_index), end_index=end_index)


def slice_sequence(sequence: PoseSequence, window: LiftWindow) -> PoseSequence:
    """Devuelve la subsecuencia contenida en la ventana.

    Los fotogramas conservan su índice original, de modo que las capas de
    dibujo pueden seguir localizándolos dentro del vídeo completo.
    """
    frames = tuple(
        frame for frame in sequence.frames if window.contains(frame.index)
    )
    return PoseSequence(frames=frames, fps=sequence.fps)