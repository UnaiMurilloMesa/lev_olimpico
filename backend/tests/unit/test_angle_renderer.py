"""Pruebas del renderizado de ángulos y de la composición de capas."""

import numpy as np

from app.domain.angles import JointName
from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.services.pose.angle_renderer import AngleRenderer, AngleStyle
from app.services.pose.composite import CompositeFrameRenderer

SIZE = 200


def _frame() -> np.ndarray:
    return np.zeros((SIZE, SIZE, 3), dtype=np.uint8)


def _pose(positions: dict[int, tuple[float, float]] | None = None) -> PoseFrame:
    landmarks = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    for index, (x, y) in (positions or {}).items():
        landmarks[index] = Landmark(x, y, 0.0, 1.0)
    return PoseFrame(index=0, timestamp_ms=0, landmarks=tuple(landmarks))


def test_no_modifica_el_fotograma_original() -> None:
    original = _frame()

    AngleRenderer().render(original, _pose())

    assert not original.any()


def test_devuelve_el_fotograma_intacto_si_no_hay_pose() -> None:
    original = _frame()
    vacia = PoseFrame(index=0, timestamp_ms=0, landmarks=())

    resultado = AngleRenderer().render(original, vacia)

    assert np.array_equal(resultado, original)


def test_dibuja_algo_sobre_el_fotograma() -> None:
    pose = _pose(
        {
            PoseLandmarkId.RIGHT_HIP: (0.5, 0.4),
            PoseLandmarkId.RIGHT_KNEE: (0.5, 0.6),
            PoseLandmarkId.RIGHT_ANKLE: (0.5, 0.8),
        }
    )

    resultado = AngleRenderer().render(_frame(), pose)

    assert resultado.any()


def test_no_dibuja_las_articulaciones_excluidas_del_estilo() -> None:
    estilo = AngleStyle(visible_joints=())

    resultado = AngleRenderer(estilo).render(_frame(), _pose())

    assert not resultado.any()


def test_las_etiquetas_no_se_salen_del_fotograma() -> None:
    """Un punto en la esquina no debe provocar recorte ni pérdida de la etiqueta."""
    pose = _pose({PoseLandmarkId.RIGHT_KNEE: (0.99, 0.01)})
    estilo = AngleStyle(visible_joints=(JointName.RIGHT_KNEE,))

    resultado = AngleRenderer(estilo).render(_frame(), pose)

    assert resultado.shape == (SIZE, SIZE, 3)
    assert resultado.any()


def test_el_compuesto_aplica_todos_los_renderizadores_en_orden() -> None:
    class Marcador:
        def __init__(self, valor: int, registro: list[int]) -> None:
            self._valor = valor
            self._registro = registro

        def render(self, frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
            self._registro.append(self._valor)
            return frame_bgr

    registro: list[int] = []
    compuesto = CompositeFrameRenderer(Marcador(1, registro), Marcador(2, registro))

    compuesto.render(_frame(), _pose())

    assert registro == [1, 2]


def test_el_compuesto_sin_renderizadores_devuelve_el_fotograma() -> None:
    original = _frame()

    resultado = CompositeFrameRenderer().render(original, _pose())

    assert np.array_equal(resultado, original)