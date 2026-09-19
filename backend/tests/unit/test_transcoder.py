"""Pruebas del conversor de vídeo basado en ffmpeg."""

from pathlib import Path

import pytest

from app.services.video.transcoder import FfmpegTranscoder, TranscodingError


def test_construye_el_comando_con_los_parametros_de_compatibilidad() -> None:
    transcoder = FfmpegTranscoder(crf=20, preset="fast")

    command = transcoder._build_command(Path("in.mp4"), Path("out.mp4"))

    assert "libx264" in command
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert command[command.index("-crf") + 1] == "20"
    assert command[command.index("-preset") + 1] == "fast"
    assert "+faststart" in command


def test_detecta_que_el_binario_no_existe() -> None:
    assert FfmpegTranscoder(binary="ffmpeg-inexistente-xyz").is_available is False


def test_falla_si_ffmpeg_no_esta_disponible(tmp_path: Path) -> None:
    transcoder = FfmpegTranscoder(binary="ffmpeg-inexistente-xyz")

    with pytest.raises(TranscodingError, match="No se encontró"):
        transcoder.to_android_compatible(tmp_path / "in.mp4", tmp_path / "out.mp4")