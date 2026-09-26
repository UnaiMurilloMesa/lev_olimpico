"""Dibujo de los ángulos articulares sobre el fotograma."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.domain.angles import JOINT_DEFINITIONS, JointName, joint_angles
from app.domain.landmarks import PoseFrame

# Con el estándar de grabación a 45º lateral derecho, las articulaciones del
# lado derecho son las que quedan visibles y fiables.
DEFAULT_VISIBLE_JOINTS: tuple[JointName, ...] = (
    JointName.RIGHT_ELBOW,
    JointName.RIGHT_HIP,
    JointName.RIGHT_KNEE,
    JointName.RIGHT_ANKLE,
)

TEXT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (0, 0, 0)


@dataclass(frozen=True)
class AngleStyle:
    """Parámetros visuales de las etiquetas de ángulo."""

    font_scale: float = 0.5
    thickness: int = 1
    offset_x: int = 10
    offset_y: int = -8
    padding: int = 3
    visible_joints: tuple[JointName, ...] = field(default=DEFAULT_VISIBLE_JOINTS)


class AngleRenderer:
    """Escribe junto a cada articulación el valor de su ángulo."""

    def __init__(self, style: AngleStyle | None = None) -> None:
        """Crea el renderizador con el estilo indicado o el predeterminado."""
        self._style = style or AngleStyle()

    def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Devuelve una copia del fotograma con los ángulos anotados."""
        canvas = frame_bgr.copy()
        angles = joint_angles(pose)
        if not angles:
            return canvas

        height, width = canvas.shape[:2]
        for joint in self._style.visible_joints:
            angle = angles.get(joint)
            if angle is None:
                continue
            vertex = pose.landmarks[JOINT_DEFINITIONS[joint].vertex]
            self._draw_label(canvas, f"{angle:.0f}", vertex.to_pixels(width, height))

        return canvas

    def _draw_label(self, canvas: np.ndarray, text: str, anchor: tuple[int, int]) -> None:
        """Dibuja una etiqueta legible sobre un fondo opaco."""
        style = self._style
        origin_x = anchor[0] + style.offset_x
        origin_y = anchor[1] + style.offset_y

        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, style.font_scale, style.thickness
        )
        origin_x, origin_y = self._clamp_origin(
            canvas, origin_x, origin_y, text_width, text_height
        )

        cv2.rectangle(
            canvas,
            (origin_x - style.padding, origin_y - text_height - style.padding),
            (origin_x + text_width + style.padding, origin_y + baseline),
            BACKGROUND_COLOR,
            thickness=-1,
        )
        cv2.putText(
            canvas,
            text,
            (origin_x, origin_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            style.font_scale,
            TEXT_COLOR,
            style.thickness,
            cv2.LINE_AA,
        )

    @staticmethod
    def _clamp_origin(
        canvas: np.ndarray, x: int, y: int, text_width: int, text_height: int
    ) -> tuple[int, int]:
        """Mantiene la etiqueta dentro de los límites de la imagen."""
        height, width = canvas.shape[:2]
        x = max(0, min(x, width - text_width - 1))
        y = max(text_height + 1, min(y, height - 1))
        return x, y