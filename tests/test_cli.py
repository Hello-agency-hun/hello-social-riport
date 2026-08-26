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
            "--allow-fixture",
            *extra,
        ]
    )


def test_the_fixture_cannot_be_used_as_a_client_folder(fixture_dir, capsys):
    """A fixture valódi ügyféladat, teljes exportkészlettel és kész
    narratívával — semmi nem különbözteti meg egy éles munkamappától.

    Egy agent, akit megkérnek, hogy „csinálj riportot a Larusnak júliusra”,
    rátalál és épít belőle. Ez meg is történt Codexen: a riport hibátlan lett,
    csak épp nem arról szólt, amit a menedzser feltöltött — és ez sehol nem
    derült ki. Leírni, hogy ne tegye, nem elég."""
    exit_code = main([str(fixture_dir), "--period", "2026-07", "--validate"])

    assert exit_code == 1
    error = capsys.readouterr().err
    assert "teszt-fixture, nem ügyfélmappa" in error
    assert "clients/" in error, "mondjuk meg, hova tegye helyette"


def test_validate_prints_data_map(fixture_dir, capsys):
    exit_code = main(
        [str(fixture_dir), "--period", "2026-07", "--validate", "--allow-fixture"]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "29 tartalom" in out
    assert "16 mért organikus teljesítménnyel" in out
    assert "472.71 EUR" in out
    # Az „illesztetlen boost" a leggyakrabban NEM hiba: a poszt egy korábbi
    # hónapban jelent meg, a hirdetés viszont most futott rá. A kimenet ezért
    # mindkét esetet megnevezi, nem figyelmeztetésként.
    assert "Minden boost megtalálta a posztját." in out


def test_validate_names_how_the_exact_period_was_resolved(fixture_dir, capsys):
    exit_code = main(
        [str(fixture_dir), "--period", "2026-07", "--validate", "--allow-fixture"]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "napi exportokból" in out
    assert "2026-07-01 – 2026-07-31" in out


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


def test_cli_accepts_exact_date_overrides(fixture_dir, tmp_path):
    target = tmp_path / "report_data.json"
    exit_code = main(
        [
            str(fixture_dir),
            "--period", "2026-06",
            "--start-date", "2026-07-01",
            "--end-date", "2026-07-31",
            "--out", str(target),
            "--html", str(tmp_path / "Riport.html"),
            "--offline", "--allow-fixture",
        ]
    )

    assert exit_code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["meta"]["period"] == "2026-07"


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
            "--offline", "--allow-fixture",
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


def test_apply_review_writes_the_edits_into_the_narrative(fixture_dir, tmp_path):
    import shutil

    work = tmp_path / "larus"
    shutil.copytree(fixture_dir, work)
    (work / "narrative.json").write_text(
        json.dumps({"executive_summary": "Eredeti szöveg."}), encoding="utf-8"
    )
    (work / "review.json").write_text(
        json.dumps({"edits": {"executive_summary": "Átírt szöveg."}}), encoding="utf-8"
    )

    exit_code = main(
        [
            str(work), "--period", "2026-07", "--apply-review",
            "--out", str(tmp_path / "d.json"),
            "--html", str(tmp_path / "r.html"), "--offline",
        ]
    )
    assert exit_code == 0
    narrative = json.loads((work / "narrative.json").read_text(encoding="utf-8"))
    assert narrative["executive_summary"] == "Átírt szöveg."


def test_comments_are_reported_to_the_manager(fixture_dir, tmp_path, capsys):
    import shutil

    work = tmp_path / "larus"
    shutil.copytree(fixture_dir, work)
    (work / "review.json").write_text(
        json.dumps({"comments": [{"page": 12, "text": "ide kérek kördiagramot"}]}),
        encoding="utf-8",
    )
    main(
        [
            str(work), "--period", "2026-07", "--apply-review",
            "--out", str(tmp_path / "d.json"),
            "--html", str(tmp_path / "r.html"), "--offline",
        ]
    )
    assert "ide kérek kördiagramot" in capsys.readouterr().out


def test_apply_review_leaves_the_narrative_alone_without_a_review_file(
    fixture_dir, tmp_path
):
    """Review nélkül a `--apply-review` nem nyúl a narratívához."""
    import shutil

    work = tmp_path / "larus"
    shutil.copytree(fixture_dir, work)
    before = (work / "narrative.json").read_text(encoding="utf-8")

    exit_code = main(
        [
            str(work), "--period", "2026-07", "--apply-review",
            "--out", str(tmp_path / "d.json"),
            "--html", str(tmp_path / "r.html"), "--offline",
        ]
    )
    assert exit_code == 0
    assert (work / "narrative.json").read_text(encoding="utf-8") == before
