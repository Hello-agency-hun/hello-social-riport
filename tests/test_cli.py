import json
from pathlib import Path

from pipeline.cli import main


def run(fixture_dir, tmp_path, *extra):
    """A CLI hívása úgy, hogy semmit ne írjon a fixture mappájába, és ne
    hálózatozzon. Enélkül a tesztek szemetelnének a repóba és lassúak lennének."""
    return main(
        [
            str(fixture_dir),
            "--period",
            "2026-07",
            "--out",
            str(tmp_path / "report_data.json"),
            "--html",
            str(tmp_path / "Riport.html"),
            "--offline",
            *extra,
        ]
    )


def test_validate_prints_data_map(fixture_dir, capsys):
    exit_code = main([str(fixture_dir), "--period", "2026-07", "--validate"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "29 tartalom" in out
    assert "15/16" in out
    assert "472.71 EUR" in out
    assert "nem illesztett boost" in out


def test_validate_writes_nothing(fixture_dir, tmp_path):
    target = tmp_path / "report_data.json"
    main([str(fixture_dir), "--period", "2026-07", "--validate", "--out", str(target)])
    assert not target.exists()


def test_build_writes_report_data(fixture_dir, tmp_path):
    target = tmp_path / "report_data.json"
    exit_code = run(fixture_dir, tmp_path)
    assert exit_code == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["cross"]["reach_multiplier"] == 33.2


def test_wrong_period_exits_with_error(fixture_dir, capsys):
    exit_code = main([str(fixture_dir), "--period", "2026-06"])
    assert exit_code == 1
    assert "HIBA" in capsys.readouterr().err


def test_output_matches_the_golden_file(fixture_dir, tmp_path):
    run(fixture_dir, tmp_path)
    produced = json.loads(
        (tmp_path / "report_data.json").read_text(encoding="utf-8")
    )
    golden = json.loads(
        (Path(fixture_dir) / "report_data.golden.json").read_text(encoding="utf-8")
    )
    assert produced == golden


def test_cli_survives_a_cp1250_console(fixture_dir, tmp_path, monkeypatch):
    """Magyar Windows konzolon a cp1250 nem tudja kódolni az `⚠`-t.

    Enélkül a CLI a kiírásnál elszállna, még a report_data.json megírása előtt.
    """
    import io as _io
    import sys

    stdout = _io.TextIOWrapper(_io.BytesIO(), encoding="cp1250", errors="strict")
    monkeypatch.setattr(sys, "stdout", stdout)

    target = tmp_path / "report_data.json"
    exit_code = run(fixture_dir, tmp_path)

    assert exit_code == 0
    assert target.exists(), "a riportadat akkor is megíródik, ha a konzol szűk"


def test_render_writes_the_html(fixture_dir, tmp_path):
    target = tmp_path / "Riport.html"
    exit_code = main(
        [
            str(fixture_dir), "--period", "2026-07",
            "--out", str(tmp_path / "report_data.json"),
            "--html", str(target),
            "--offline",
        ]
    )
    assert exit_code == 0
    html = target.read_text(encoding="utf-8")
    assert "Larus Étterem" in html
    assert html.startswith("<!doctype html>")


def test_validate_does_not_render(fixture_dir, tmp_path):
    run(fixture_dir, tmp_path, "--validate")
    assert not (tmp_path / "Riport.html").exists()


def test_cli_never_writes_into_the_client_folder(fixture_dir, tmp_path):
    """A tesztek nem szemetelhetnek a verziókezelt fixture-be."""
    before = {p.name for p in Path(fixture_dir).iterdir()}
    run(fixture_dir, tmp_path)
    assert {p.name for p in Path(fixture_dir).iterdir()} == before
