"""Composición de varios renderizadores sobre un mismo fotograma."""

from __future__ import annotations

import numpy as np

from app.domain.landmarks import PoseFrame
from app.services.pose.renderer import FrameRenderer


class CompositeFrameRenderer:
    """Aplica en orden una secuencia de renderizadores sobre el fotograma.

    Permite añadir capas de información (esqueleto, ángulos, trayectoria de la
    barra) sin que ninguna de ellas conozca a las demás.
    """

    def __init__(self, *renderers: FrameRenderer) -> None:
        """Crea el compuesto con los renderizadores indicados, en orden de dibujo."""
        self._renderers = renderers

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Devuelve el fotograma tras pasar por todos los renderizadores."""
        canvas = frame_bgr
        for renderer in self._renderers:
            canvas = renderer.render(canvas, pose)
        return canvas