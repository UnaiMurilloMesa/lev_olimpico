"""Configuración de logging de la aplicación."""

import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """Inicializa el logging raíz con un formato homogéneo."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("absl").setLevel(logging.WARNING)
