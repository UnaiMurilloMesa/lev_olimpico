"""Pruebas de la limpieza de espacios de trabajo caducados."""

import os
import time
from pathlib import Path

from app.services.cleanup import WorkspaceCleaner

ONE_HOUR = 3600


def _workspace(root: Path, name: str, age_seconds: float, size: int = 100) -> Path:
    """Crea un espacio de trabajo con la antigüedad indicada."""
    path = root / name
    path.mkdir(parents=True)
    fichero = path / "analysis.mp4"
    fichero.write_bytes(b"x" * size)

    timestamp = time.time() - age_seconds
    os.utime(fichero, (timestamp, timestamp))
    os.utime(path, (timestamp, timestamp))
    return path


def test_elimina_los_espacios_caducados(tmp_path: Path) -> None:
    viejo = _workspace(tmp_path, "viejo", age_seconds=2 * ONE_HOUR)

    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean()

    assert not viejo.exists()
    assert informe.removed == 1


def test_conserva_los_espacios_recientes(tmp_path: Path) -> None:
    reciente = _workspace(tmp_path, "reciente", age_seconds=60)

    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean()

    assert reciente.exists()
    assert informe.removed == 0


def test_conserva_un_analisis_en_curso_aunque_el_directorio_sea_antiguo(
    tmp_path: Path,
) -> None:
    """Un trabajo largo escribe ficheros nuevos en un directorio ya antiguo."""
    workspace = _workspace(tmp_path, "en-curso", age_seconds=2 * ONE_HOUR)
    (workspace / "nuevo.jpg").write_bytes(b"reciente")

    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean()

    assert workspace.exists()
    assert informe.removed == 0


def test_informa_del_espacio_liberado(tmp_path: Path) -> None:
    _workspace(tmp_path, "viejo", age_seconds=2 * ONE_HOUR, size=2_097_152)

    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean()

    assert informe.freed_megabytes == 2.0


def test_cuenta_los_directorios_inspeccionados(tmp_path: Path) -> None:
    _workspace(tmp_path, "uno", age_seconds=2 * ONE_HOUR)
    _workspace(tmp_path, "dos", age_seconds=60)

    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean()

    assert informe.inspected == 2
    assert informe.removed == 1


def test_ignora_los_ficheros_sueltos(tmp_path: Path) -> None:
    (tmp_path / "suelto.txt").write_text("no es un espacio de trabajo")

    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean()

    assert informe.inspected == 0


def test_un_almacenamiento_inexistente_no_falla(tmp_path: Path) -> None:
    informe = WorkspaceCleaner(tmp_path / "no-existe", ONE_HOUR).clean()

    assert informe.inspected == 0


def test_el_instante_de_referencia_es_inyectable(tmp_path: Path) -> None:
    """Permite probar la caducidad sin depender del reloj real."""
    _workspace(tmp_path, "reciente", age_seconds=60)

    futuro = time.time() + 2 * ONE_HOUR
    informe = WorkspaceCleaner(tmp_path, ONE_HOUR).clean(now=futuro)

    assert informe.removed == 1