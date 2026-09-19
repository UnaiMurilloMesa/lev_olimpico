"""Pruebas del gestor de espacios de trabajo."""

from pathlib import Path

from app.services.workspace import JobWorkspace

JOB_ID = "11111111-2222-3333-4444-555555555555"


def test_el_directorio_lleva_el_identificador_del_trabajo(tmp_path: Path) -> None:
    workspace = JobWorkspace(tmp_path, JOB_ID)

    assert workspace.path == tmp_path / JOB_ID


def test_crea_el_directorio(tmp_path: Path) -> None:
    workspace = JobWorkspace(tmp_path, JOB_ID)

    workspace.create()

    assert workspace.exists() is True


def test_crear_dos_veces_no_falla(tmp_path: Path) -> None:
    workspace = JobWorkspace(tmp_path, JOB_ID)

    workspace.create()
    workspace.create()

    assert workspace.exists() is True


def test_trabajos_distintos_no_comparten_directorio(tmp_path: Path) -> None:
    primero = JobWorkspace(tmp_path, "job-a")
    segundo = JobWorkspace(tmp_path, "job-b")

    assert primero.path != segundo.path


def test_localiza_el_video_original_con_cualquier_extension(tmp_path: Path) -> None:
    workspace = JobWorkspace(tmp_path, JOB_ID)
    workspace.create()
    workspace.source_path(".mov").write_bytes(b"contenido")

    encontrado = workspace.find_source()

    assert encontrado is not None
    assert encontrado.suffix == ".mov"


def test_devuelve_none_si_no_hay_video_original(tmp_path: Path) -> None:
    workspace = JobWorkspace(tmp_path, JOB_ID)
    workspace.create()

    assert workspace.find_source() is None


def test_elimina_el_directorio_con_su_contenido(tmp_path: Path) -> None:
    workspace = JobWorkspace(tmp_path, JOB_ID)
    workspace.create()
    workspace.result_path("analysis.mp4").write_bytes(b"video")

    workspace.delete()

    assert workspace.exists() is False


def test_eliminar_un_directorio_inexistente_no_falla(tmp_path: Path) -> None:
    JobWorkspace(tmp_path, JOB_ID).delete()