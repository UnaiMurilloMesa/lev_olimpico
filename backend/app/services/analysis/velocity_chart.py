"""Generación de la gráfica de velocidad de la barra."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import matplotlib

matplotlib.use("Agg")  # Backend sin ventana, obligatorio en el contenedor.

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402

from app.services.analysis.velocity import BarVelocity  # noqa: E402

logger = logging.getLogger(__name__)

LINE_COLOR = "#1f77b4"
PEAK_COLOR = "#d62728"
GRID_COLOR = "#dddddd"


@dataclass(frozen=True, slots=True)
class ChartStyle:
    """Parámetros visuales de la gráfica."""

    width_inches: float = 8.0
    height_inches: float = 4.0
    dpi: int = 110
    line_width: float = 2.0


class VelocityChartRenderer(Protocol):
    """Contrato de cualquier generador de gráficas de velocidad."""

    def render(self, velocity: BarVelocity, destination: Path) -> Path:
        """Genera la gráfica y devuelve la ruta del fichero creado."""
        ...


class MatplotlibVelocityChart:
    """Dibuja la velocidad vertical de la barra como imagen PNG."""

    def __init__(self, style: ChartStyle | None = None) -> None:
        """Crea el generador con el estilo indicado."""
        self._style = style or ChartStyle()

    def render(self, velocity: BarVelocity, destination: Path) -> Path:
        """Genera la gráfica de velocidad en la ruta indicada."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        times, values = velocity.as_series()

        figure, axes = plt.subplots(
            figsize=(self._style.width_inches, self._style.height_inches),
            dpi=self._style.dpi,
        )
        try:
            self._draw(axes, times, values, velocity)
            figure.tight_layout()
            figure.savefig(destination, format="png")
        finally:
            # Sin cierre explícito, matplotlib acumula figuras en memoria y el
            # worker acaba agotándola tras varios análisis.
            plt.close(figure)

        logger.info("Gráfica de velocidad generada en %s", destination)
        return destination

    def _draw(
        self,
        axes: Axes,
        times: list[float],
        values: list[float],
        velocity: BarVelocity,
    ) -> None:
        """Dibuja la serie, los ejes y la marca de velocidad máxima."""
        axes.plot(times, values, color=LINE_COLOR, linewidth=self._style.line_width)
        axes.axhline(0, color="#888888", linewidth=1)
        axes.grid(True, color=GRID_COLOR, linestyle="--", linewidth=0.6)

        axes.set_title("Velocidad vertical de la barra")
        axes.set_xlabel("Tiempo (s)")
        axes.set_ylabel("Velocidad (m/s)")

        if not times:
            axes.text(
                0.5,
                0.5,
                "Sin datos de velocidad",
                ha="center",
                va="center",
                transform=axes.transAxes,
            )
            return

        axes.set_xlim(min(times), max(times))
        self._mark_peak(axes, velocity)

    @staticmethod
    def _mark_peak(axes: Axes, velocity: BarVelocity) -> None:
        """Señala el instante de velocidad ascendente máxima."""
        peak = velocity.peak
        if peak is None or peak.velocity_ms <= 0:
            return

        axes.axvline(peak.time_seconds, color=PEAK_COLOR, linestyle=":", linewidth=1.2)
        axes.plot(peak.time_seconds, peak.velocity_ms, "o", color=PEAK_COLOR, markersize=6)
        axes.annotate(
            f"{peak.velocity_ms:.2f} m/s",
            xy=(peak.time_seconds, peak.velocity_ms),
            xytext=(6, 6),
            textcoords="offset points",
            color=PEAK_COLOR,
            fontsize=9,
        )