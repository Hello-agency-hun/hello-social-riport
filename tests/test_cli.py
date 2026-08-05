import json
from pathlib import Path

from pipeline.cli import main


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
    exit_code = main([str(fixture_dir), "--period", "2026-07", "--out", str(target)])
    assert exit_code == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["cross"]["reach_multiplier"] == 33.2


def test_wrong_period_exits_with_error(fixture_dir, capsys):
    exit_code = main([str(fixture_dir), "--period", "2026-06"])
    assert exit_code == 1
    assert "HIBA" in capsys.readouterr().err


def test_output_matches_the_golden_file(fixture_dir, tmp_path):
    target = tmp_path / "report_data.json"
    main([str(fixture_dir), "--period", "2026-07", "--out", str(target)])
    produced = json.loads(target.read_text(encoding="utf-8"))
    golden = json.loads(
        (Path(fixture_dir) / "report_data.golden.json").read_text(encoding="utf-8")
    )
    assert produced == golden
