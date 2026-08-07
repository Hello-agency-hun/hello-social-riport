"""Ami az input mappába kerül, de nem export.

A menedzser nem laboratóriumban dolgozik. Letölti rossz formátumban, bedobja a
Business Suite képernyőképeit, vagy megnyitja Excelben és menti. Ezek egyike sem
hiba — csak tudnunk kell, mi az, hogy értelmesen tudjunk szólni róla.
"""

import shutil

import pytest

from pipeline.build import build
from pipeline.detect import sniff
from pipeline.errors import WrongFormatError

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"\x00" * 32
LEGACY = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32


@pytest.mark.parametrize(
    "raw,expected",
    [(PNG, "screenshot"), (JPEG, "screenshot"), (PDF, "pdf"),
     (LEGACY, "legacy_office")],
    ids=["png", "jpeg", "pdf", "regi-xls"],
)
def test_the_content_decides_not_the_extension(tmp_path, raw, expected):
    """A kiterjesztés hazudhat: a Business Suite képét `.csv` néven is el
    lehet menteni. Az első bájtok nem hazudnak."""
    path = tmp_path / "akarmi.csv"
    path.write_bytes(raw)
    assert sniff(path) == expected


def test_screenshots_are_not_an_error(fixture_dir, tmp_path):
    """A menedzser gyakran bedobja a Business Suite képernyőképeit is. Ezekről
    a hiányzó számok leolvashatók — ez segítség, nem szemét."""
    work = tmp_path / "kepekkel"
    shutil.copytree(fixture_dir, work)
    (work / "input" / "business-suite-eleres.png").write_bytes(PNG)

    data = build(work, period="2026-07")
    assert data["screenshots"] == ["business-suite-eleres.png"]


def test_a_pdf_says_what_to_do_with_it(fixture_dir, tmp_path):
    """„Ismeretlen fájl” itt haszontalan válasz: a tartalma jó lehet, csak a
    formátuma nem az."""
    work = tmp_path / "pdf-fel"
    shutil.copytree(fixture_dir, work)
    (work / "input" / "zoomsphere.pdf").write_bytes(PDF)

    with pytest.raises(WrongFormatError) as caught:
        build(work, period="2026-07")

    message = str(caught.value)
    assert "zoomsphere.pdf" in message
    assert "XLSX" in message, "mondjuk meg, mit töltsön le helyette"
    assert "átalakítom" in message, "és azt is, hogy van másik út"


def test_a_legacy_excel_is_named_as_such(fixture_dir, tmp_path):
    work = tmp_path / "regi-xls"
    shutil.copytree(fixture_dir, work)
    (work / "input" / "kampanyok.xls").write_bytes(LEGACY)

    with pytest.raises(WrongFormatError) as caught:
        build(work, period="2026-07")

    assert ".xls" in str(caught.value)


def test_screenshots_do_not_stop_the_build(fixture_dir, tmp_path):
    """Egy kép nem akadályozhatja meg a riport elkészülését."""
    work = tmp_path / "vegyes"
    shutil.copytree(fixture_dir, work)
    (work / "input" / "kep1.png").write_bytes(PNG)
    (work / "input" / "kep2.jpg").write_bytes(JPEG)

    data = build(work, period="2026-07")
    assert len(data["screenshots"]) == 2
    assert data["cross"]["posts_total"] > 0
