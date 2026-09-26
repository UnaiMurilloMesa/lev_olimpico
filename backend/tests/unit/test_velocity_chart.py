"""Pruebas de la gráfica de velocidad."""

from pathlib import Path

from app.services.analysis.velocity import BarVelocity, VelocitySample
from app.services.analysis.velocity_chart import ChartStyle, MatplotlibVelocityChart

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _velocity(*values: float) -> BarVelocity:
    return BarVelocity(
        samples=tuple(
            VelocitySample(frame_index=index, time_seconds=index / 30.0, velocity_ms=value)
            for index, value in enumerate(values)
        )
    )


def test_genera_un_fichero_png(tmp_path: Path) -> None:
    destino = tmp_path / "velocidad.png"

    MatplotlibVelocityChart().render(_velocity(0.1, 0.5, 1.2, 0.8), destino)

    assert destino.is_file()
    assert destino.read_bytes().startswith(PNG_SIGNATURE)


def test_crea_los_directorios_intermedios(tmp_path: Path) -> None:
    destino = tmp_path / "nivel1" / "nivel2" / "velocidad.png"

    MatplotlibVelocityChart().render(_velocity(0.1, 0.5), destino)

    assert destino.is_file()


def test_una_serie_vacia_genera_igualmente_la_grafica(tmp_path: Path) -> None:
    destino = tmp_path / "vacia.png"

    MatplotlibVelocityChart().render(BarVelocity(samples=()), destino)

    assert destino.is_file()
    assert destino.stat().st_size > 0


def test_respeta_las_dimensiones_configuradas(tmp_path: Path) -> None:
    estilo = ChartStyle(width_inches=4.0, height_inches=2.0, dpi=100)
    destino = tmp_path / "pequena.png"

    MatplotlibVelocityChart(estilo).render(_velocity(0.1, 0.5, 1.0), destino)

    # Cabecera PNG: ancho y alto en píxeles, big-endian, tras los 16 primeros bytes.
    header = destino.read_bytes()[16:24]
    width = int.from_bytes(header[:4], "big")
    height = int.from_bytes(header[4:], "big")
    assert (width, height) == (400, 200)


def test_una_serie_solo_negativa_no_falla(tmp_path: Path) -> None:
    """Sin pico ascendente no debe intentarse anotar el máximo."""
    destino = tmp_path / "negativa.png"

    MatplotlibVelocityChart().render(_velocity(-0.3, -0.8, -0.5), destino)

    assert destino.is_file()


def test_no_acumula_figuras_en_memoria(tmp_path: Path) -> None:
    import matplotlib.pyplot as plt

    for index in range(5):
        MatplotlibVelocityChart().render(_velocity(0.1, 0.9), tmp_path / f"{index}.png")

    assert plt.get_fignums() == []
