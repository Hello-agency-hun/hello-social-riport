"""Meddig ér az adat, és illeszkedik-e az előző hónaphoz.

A Mammut-próba mutatta meg, mennyibe kerül ennek a hiánya: a korábbi, kézi
riportok metrikánként hét-tíz nappal eltérő napokon zárultak, egyetlen
dokumentumon belül. A belőlük számolt „változás" nem változás volt, hanem
mérési különbség — és sehol nem látszott.
"""

import shutil

import pytest

from pipeline import compare
from pipeline.build import build
from pipeline.errors import MeasurementPeriodError
from pipeline.render import _measured_range
from pipeline.textio import read_text


def test_the_measured_range_comes_from_the_files(fixture_dir):
    meta = build(fixture_dir, period="2026-07")["meta"]

    assert meta["coverage_start"] == "2026-07-01"
    assert meta["coverage_end"] == "2026-07-31"
    assert meta["coverage_partial"] is False


def test_a_mid_month_download_is_not_reported_as_a_full_month(fixture_dir, tmp_path):
    """A menedzser nem mindig a hónap utolsó napján tölt le. Ha ilyenkor teljes
    hónapot állítanánk, a következő havi összehasonlítás csendben torz lenne."""
    work = tmp_path / "felbeszakadt"
    shutil.copytree(fixture_dir, work)

    # A Meta exportjai vegyesen UTF-16 és UTF-8 BOM-osak — a saját olvasónk
    # kezeli, a nyers `read_text` nem.
    from pipeline.textio import read_text

    for path in (work / "input").glob("*.csv"):
        lines = read_text(path).splitlines()
        if lines and lines[0].lower().startswith("sep="):
            keep = [
                line
                for line in lines
                if "2026-07-2" not in line and "2026-07-3" not in line
            ]
            path.write_text("\n".join(keep) + "\n", encoding="utf-8")

    meta = build(work, period="2026-07")["meta"]
    assert meta["measurement_end"] < "2026-07-31"
    assert meta["measurement_credibility"] == "nonstandard"
    assert meta["coverage_partial"] is False


def test_daily_exports_with_different_end_dates_are_rejected(fixture_dir, tmp_path):
    work = tmp_path / "eltolt-csempe"
    shutil.copytree(fixture_dir, work)
    path = work / "input" / "Felkeresések.csv"
    lines = read_text(path).splitlines()
    path.write_text(
        "\n".join(line for line in lines if "2026-07-31" not in line) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(MeasurementPeriodError, match="eltérő időszakokat"):
        build(work, period="2026-07")


def test_the_report_shows_the_measured_range_not_the_calendar_month():
    partial = {"period": "2026-07", "coverage_start": "2026-07-01",
               "coverage_end": "2026-07-24"}
    assert _measured_range(partial) == "2026-07-01 – 2026-07-24"

    # Régi riportadatban nincs lefedettség — ilyenkor a naptári hónap a
    # legjobb, amit mondhatunk.
    assert _measured_range({"period": "2026-07"}) == "2026-07-01 – 2026-07-31"


def _meta(start="2026-07-01"):
    return {"coverage_start": start, "coverage_end": "2026-07-31"}


def test_a_contiguous_previous_month_is_fine():
    previous = {"meta": {"coverage_end": "2026-06-30"}}
    assert compare.coverage_check(previous, _meta())["status"] == "ok"


def test_a_gap_between_the_two_periods_is_named():
    """Ha az előző hónap huszonnegyedikén zárult, hat nap kimarad — és a
    változás ezekkel nem számol."""
    previous = {"meta": {"coverage_end": "2026-06-24"}}
    found = compare.coverage_check(previous, _meta())

    assert found["status"] == "gap"
    assert "6 nap hiányzik" in found["message"]


def test_an_overlap_is_named_too():
    """Átfedésnél a közös napok mindkét oldalon szerepelnek, tehát a változás
    kisebbnek látszik a valóságosnál."""
    previous = {"meta": {"coverage_end": "2026-07-05"}}
    found = compare.coverage_check(previous, _meta())

    assert found["status"] == "overlap"
    assert "átfed" in found["message"]


def test_a_previous_report_without_coverage_is_flagged_as_unknown():
    """Ez a valós eset: kézi riportból vagy PDF-ből származó előzmény. Nem
    állítjuk, hogy illeszkedik — de azt sem, hogy nem."""
    found = compare.coverage_check({"meta": {"period": "2026-06"}}, _meta())

    assert found["status"] == "unknown"
    assert "mérési különbség" in found["message"]


def test_no_previous_month_is_not_a_problem():
    assert compare.coverage_check(None, _meta())["status"] == "none"


def test_comparison_prefers_exact_measurement_dates_over_legacy_coverage():
    previous = {
        "meta": {
            "measurement_end": "2026-07-24",
            "coverage_end": "2026-07-31",
        }
    }
    current = {
        "measurement_start": "2026-07-25",
        "coverage_start": "2026-08-01",
    }

    found = compare.coverage_check(previous, current)

    assert found["status"] == "ok"
    assert found["previous_end"] == "2026-07-24"
