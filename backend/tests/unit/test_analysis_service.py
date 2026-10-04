"""Pruebas del servicio de análisis con dobles de prueba."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.domain.landmarks import Landmark, PoseFrame, PoseLandmarkId
from app.domain.phases import PhaseBreakdown
from app.domain.sequence import PoseSequence
from app.services.analysis.velocity import BarVelocity
from app.services.analysis_service import FINAL_OUTPUT_NAME, AnalysisService
from app.services.video.metadata import VideoMetadata
from app.services.video.snapshots import PhaseSnapshot

FRAMES = 5


class FakeExtractor:
    """Extractor que devuelve una secuencia fija sin abrir el vídeo."""

    def __init__(self, detected: int = FRAMES) -> None:
        self._detected = detected

    def extract(self, source: Path) -> tuple[PoseSequence, VideoMetadata]:
        frames = tuple(
            PoseFrame(
                index=index,
                timestamp_ms=index * 33,
                landmarks=self._landmarks(index) if index < self._detected else (),
            )
            for index in range(FRAMES)
        )
        metadata = VideoMetadata(width=64, height=48, fps=30.0, frame_count=FRAMES)
        return PoseSequence(frames=frames, fps=30.0), metadata

    @staticmethod
    def _landmarks(index: int) -> tuple[Landmark, ...]:
        """Pose con cuerpo extendido y barra subiendo, para que haya escala."""
        points = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
        for eye in (PoseLandmarkId.LEFT_EYE, PoseLandmarkId.RIGHT_EYE):
            points[eye] = Landmark(0.5, 0.1, 0.0, 1.0)
        for foot in (
            PoseLandmarkId.LEFT_HEEL,
            PoseLandmarkId.RIGHT_HEEL,
            PoseLandmarkId.LEFT_FOOT_INDEX,
            PoseLandmarkId.RIGHT_FOOT_INDEX,
        ):
            points[foot] = Landmark(0.5, 0.9, 0.0, 1.0)
        bar_y = 0.8 - 0.05 * index
        for wrist in (PoseLandmarkId.LEFT_WRIST, PoseLandmarkId.RIGHT_WRIST):
            points[wrist] = Landmark(0.5, bar_y, 0.0, 1.0)
        return tuple(points)


class SpySmoother:
    """Suavizador que registra la secuencia recibida y la devuelve igual."""

    def __init__(self) -> None:
        self.calls = 0

    def smooth(self, sequence: PoseSequence) -> PoseSequence:
        self.calls += 1
        return sequence


class FakeVideoRenderer:
    """Renderizador que crea el fichero de salida sin decodificar nada."""

    def __init__(self) -> None:
        self.sequences: list[PoseSequence] = []

    def render(
        self,
        source: Path,
        destination: Path,
        sequence: PoseSequence,
        metadata: VideoMetadata,
        lift: PoseSequence | None = None,
    ) -> Path:
        self.sequences.append(sequence)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"video-renderizado")
        return destination


class FakeChartRenderer:
    """Generador de gráficas que crea un fichero vacío."""

    def render(self, velocity: BarVelocity, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"png")
        return destination


class FakeTranscoder:
    """Conversor falso que copia el contenido y registra las llamadas."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def to_android_compatible(self, source: Path, destination: Path) -> Path:
        self.calls.append((source, destination))
        destination.write_bytes(source.read_bytes())
        return destination


class FillingSmoother:
    """Suavizador que reconstruye los fotogramas sin pose, como el real."""

    def smooth(self, sequence: PoseSequence) -> PoseSequence:
        reference = next(frame for frame in sequence.frames if frame.is_detected)
        frames = tuple(
            frame if frame.is_detected
            else PoseFrame(
                index=frame.index,
                timestamp_ms=frame.timestamp_ms,
                landmarks=reference.landmarks,
            )
            for frame in sequence.frames
        )
        return PoseSequence(frames=frames, fps=sequence.fps)


class FakeSnapshotExtractor:
    """Extractor que crea una imagen vacía por fase."""

    def extract(
        self,
        source: Path,
        destination_dir: Path,
        lift: PoseSequence,
        breakdown: PhaseBreakdown,
    ) -> tuple[PhaseSnapshot, ...]:
        destination_dir.mkdir(parents=True, exist_ok=True)
        shots = []
        for span in breakdown.spans:
            path = destination_dir / f"{span.phase.value}.jpg"
            path.write_bytes(b"jpg")
            shots.append(
                PhaseSnapshot(
                    phase=span.phase,
                    frame_index=span.start_index,
                    time_seconds=span.start_index / lift.fps,
                    path=path,
                )
            )
        return tuple(shots)


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    path = tmp_path / "levantamiento.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), 30.0, (64, 48))
    for _ in range(FRAMES):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()
    return path


def _service(
    transcoder: FakeTranscoder,
    smoother: SpySmoother | FillingSmoother | None = None,
    renderer: FakeVideoRenderer | None = None,
    detected: int = FRAMES,
    snapshot_extractor: FakeSnapshotExtractor | None = None,
) -> AnalysisService:
    return AnalysisService(
        extractor=FakeExtractor(detected),
        smoother=smoother or SpySmoother(),
        video_renderer=renderer or FakeVideoRenderer(),
        transcoder=transcoder,
        chart_renderer=FakeChartRenderer(),
        snapshot_extractor=snapshot_extractor or FakeSnapshotExtractor(),
    )


def test_devuelve_el_video_final_transcodificado(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "job-1"

    result = _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert result.video_path == workspace / FINAL_OUTPUT_NAME
    assert result.video_path.is_file()


def test_invoca_la_transcodificacion_una_vez(sample_video: Path, tmp_path: Path) -> None:
    transcoder = FakeTranscoder()

    _service(transcoder).analyze(sample_video, tmp_path / "job-1")

    assert len(transcoder.calls) == 1


def test_suaviza_la_secuencia_antes_de_renderizar(sample_video: Path, tmp_path: Path) -> None:
    smoother = SpySmoother()
    renderer = FakeVideoRenderer()

    _service(FakeTranscoder(), smoother, renderer).analyze(sample_video, tmp_path / "job-1")

    assert smoother.calls == 1
    assert len(renderer.sequences) == 1


def test_elimina_el_video_intermedio(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "job-1"

    _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert list(workspace.glob("*_raw.mp4")) == []


def test_informa_de_las_estadisticas_de_deteccion(sample_video: Path, tmp_path: Path) -> None:
    result = _service(FakeTranscoder(), detected=4).analyze(sample_video, tmp_path / "job-1")

    assert result.processed_frames == FRAMES
    assert result.detected_frames == 4
    assert result.detection_ratio == pytest.approx(0.8)


def test_crea_el_directorio_de_trabajo_si_no_existe(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "nivel1" / "nivel2"

    _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert workspace.is_dir()


def test_incluye_la_valoracion_del_bar_path(sample_video: Path, tmp_path: Path) -> None:
    result = _service(FakeTranscoder()).analyze(sample_video, tmp_path / "job-1")

    assert result.bar_path_quality in {"excellent", "acceptable", "poor"}
    assert result.bar_path_deviation >= 0.0


def test_acota_el_levantamiento_desde_el_instante_indicado(
    sample_video: Path, tmp_path: Path
) -> None:
    result = _service(FakeTranscoder()).analyze(sample_video, tmp_path / "job-1", start_seconds=0.1)

    assert result.lift_start_seconds == pytest.approx(0.1, abs=0.05)
    assert result.lift_end_seconds >= result.lift_start_seconds


def test_genera_la_grafica_de_velocidad(sample_video: Path, tmp_path: Path) -> None:
    workspace = tmp_path / "job-1"

    result = _service(FakeTranscoder()).analyze(sample_video, workspace)

    assert result.velocity_chart == workspace / "velocity.png"
    assert result.velocity_chart.is_file()


def test_la_deteccion_se_mide_antes_de_interpolar(
    sample_video: Path, tmp_path: Path
) -> None:
    """La interpolación no debe inflar la proporción de detección."""
    service = _service(FakeTranscoder(), smoother=FillingSmoother(), detected=3)

    result = service.analyze(sample_video, tmp_path / "job-1")

    assert result.detected_frames == 3
    assert result.detection_ratio == pytest.approx(0.6)
    assert result.interpolated_frames == 2


def test_divide_el_analisis_en_cinco_fases(sample_video: Path, tmp_path: Path) -> None:
    result = _service(FakeTranscoder()).analyze(sample_video, tmp_path / "job-1")

    assert len(result.phases) == 5
    assert result.phases[0].phase == "first_pull"
    assert all(phase.snapshot for phase in result.phases)