"""Reconstrucción de valores ausentes en una señal temporal."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# Huecos más largos que este umbral no se reconstruyen: inventar una
# trayectoria de casi medio segundo produciría movimientos falsos.
DEFAULT_MAX_GAP_MS = 400


@dataclass(frozen=True, slots=True)
class InterpolationResult:
    """Señal reconstruida junto a la marca de qué valores son inventados."""

    values: tuple[float | None, ...]
    interpolated: tuple[bool, ...]

    @property
    def filled_count(self) -> int:
        """Número de valores reconstruidos."""
        return sum(self.interpolated)


def max_gap_frames(fps: float, milliseconds: int = DEFAULT_MAX_GAP_MS) -> int:
    """Traduce la duración máxima de hueco admisible a número de fotogramas."""
    return max(1, round(fps * milliseconds / 1000))


def interpolate_gaps(values: Sequence[float | None], max_gap: int) -> InterpolationResult:
    """Rellena linealmente los huecos interiores que no superen `max_gap`.

    Los huecos de los extremos no se reconstruyen, porque no hay dos valores
    conocidos entre los que interpolar y extrapolar produciría trayectorias
    sin respaldo en el vídeo.
    """
    filled: list[float | None] = list(values)
    flags = [False] * len(values)
    known = [index for index, value in enumerate(values) if value is not None]

    for start, end in zip(known, known[1:], strict=False):
        gap = end - start - 1
        if gap == 0 or gap > max_gap:
            continue

        origin = values[start]
        target = values[end]
        assert origin is not None and target is not None  # noqa: S101
        step = (target - origin) / (end - start)

        for offset in range(1, gap + 1):
            filled[start + offset] = origin + step * offset
            flags[start + offset] = True

    return InterpolationResult(values=tuple(filled), interpolated=tuple(flags))