"""A menedzser útja: hány körből jut el az első sikeres futásig.

A PETI-próbán ez négy kör volt. Minden `--validate` az első hibánál megáll —
muszáj, mert a többi számítás arra épül —, de a `client.yaml` hiányzó mezői
ettől függetlenül megállapíthatók. Ezeket előre megmondjuk.
"""

import shutil

import yaml

from pipeline.cli import main


def _strip_config(work, keys):
    path = work / "client.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in keys:
        config.pop(key, None)
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


def test_one_failure_reveals_every_other_gap(fixture_dir, tmp_path, capsys):
    """Négy kör helyett egy: ha valami megállítja a buildet, akkor is
    felsoroljuk, mi hiányzik még a konfigurációból."""
    work = tmp_path / "elso-honap"
    shutil.copytree(fixture_dir, work)
    _strip_config(work, ["followers", "monthly_reach", "daily_metric_overrides"])

    exit_code = main([str(work), "--period", "2026-07", "--validate", "--allow-fixture"])
    error = capsys.readouterr().err

    assert exit_code == 1
    assert "Ez úgyis hiányozni fog" in error
    assert "followers.facebook" in error
    assert "monthly_reach.facebook" in error
    assert "followers.instagram" in error
    # …és minden ponthoz ott van, hol találja meg
    assert "profil" in error and "Business Suite" in error


def test_the_extra_help_never_hides_the_real_error(fixture_dir, tmp_path, capsys):
    """A segítség sosem takarhatja el azt, ami ténylegesen megállította."""
    work = tmp_path / "csempe"
    shutil.copytree(fixture_dir, work)
    _strip_config(work, ["daily_metric_overrides"])

    main([str(work), "--period", "2026-07", "--validate", "--allow-fixture"])
    error = capsys.readouterr().err

    assert error.index("HIBA:") < error.index("Ez úgyis hiányozni fog")
    assert "nem árulja el, melyik csatornáé" in error


def test_a_complete_config_gets_no_extra_noise(fixture_dir, tmp_path, capsys):
    """Ha minden megvan, ne beszéljünk feleslegesen."""
    work = tmp_path / "teljes"
    shutil.copytree(fixture_dir, work)
    (work / "input" / "Követők.csv").unlink()  # más hibát váltunk ki

    main([str(work), "--period", "2026-07", "--validate", "--allow-fixture"])
    assert "Ez úgyis hiányozni fog" not in capsys.readouterr().err


def test_a_missing_config_file_is_not_second_guessed(tmp_path, capsys):
    """Új ügyfélnél a hibaüzenet maga adja a teljes sablont — fölé még egy
    listát tenni zaj lenne."""
    (tmp_path / "input").mkdir()

    main([str(tmp_path), "--period", "2026-07", "--validate"])
    error = capsys.readouterr().err

    assert "nincs client.yaml" in error
    assert "Ez úgyis hiányozni fog" not in error
