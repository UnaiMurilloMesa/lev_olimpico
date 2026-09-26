"""Pruebas del validador de subidas."""

import pytest

from app.services.upload_validator import InvalidUploadError, UploadValidator

EXTENSIONES = (".mp4", ".mov")
LIMITE = 1_000_000


@pytest.fixture
def validator() -> UploadValidator:
    return UploadValidator(allowed_extensions=EXTENSIONES, max_bytes=LIMITE)


def test_acepta_un_video_valido(validator: UploadValidator) -> None:
    assert validator.validate("snatch.mp4", size_bytes=5000) == ".mp4"


def test_normaliza_la_extension_a_minusculas(validator: UploadValidator) -> None:
    assert validator.validate("SNATCH.MP4", size_bytes=5000) == ".mp4"


def test_rechaza_una_extension_no_admitida(validator: UploadValidator) -> None:
    with pytest.raises(InvalidUploadError, match="no admitida"):
        validator.validate("documento.pdf", size_bytes=5000)


def test_rechaza_un_fichero_sin_nombre(validator: UploadValidator) -> None:
    with pytest.raises(InvalidUploadError, match="nombre"):
        validator.validate(None, size_bytes=5000)


def test_rechaza_un_fichero_vacio(validator: UploadValidator) -> None:
    with pytest.raises(InvalidUploadError, match="vacío"):
        validator.validate("snatch.mp4", size_bytes=0)


def test_rechaza_un_fichero_demasiado_grande(validator: UploadValidator) -> None:
    with pytest.raises(InvalidUploadError, match="límite"):
        validator.validate("snatch.mp4", size_bytes=LIMITE + 1)


def test_acepta_un_fichero_en_el_limite_exacto(validator: UploadValidator) -> None:
    assert validator.validate("snatch.mp4", size_bytes=LIMITE) == ".mp4"
