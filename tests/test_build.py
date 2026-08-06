import shutil

import pytest
import yaml

from pipeline.build import build
from pipeline.errors import (
    ClientMismatchError,
    DuplicateSourceError,
    MissingConfigError,
    NoSourceError,
    PeriodMismatchError,
)


def test_build_produces_report_data(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    assert data["meta"]["client"] == "Larus Étterem"
    assert data["meta"]["period"] == "2026-07"
    assert data["meta"]["currency"] == "EUR"


def test_build_includes_every_section(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    for key in ("content", "channels", "paid", "cross"):
        assert key in data, key


def test_build_reports_join_quality(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    quality = data["quality"]
    # 16 Facebook-poszt a Tartalom exportból + 15 Instagram-poszt a ZoomSphere-ből
    assert quality["posts_total"] == 31
    # organikus teljesítménye csak a Facebook-posztoknak van mérve
    assert quality["posts_measured"] == 16
    assert quality["posts_with_creative"] == 30
    assert quality["dropped_zero_campaign_rows"] == 16
    # az IG-posztok felépítése után minden boost illeszthető
    assert quality["unmatched_boosts"] == []


def test_unmeasured_posts_stay_out_of_the_averages(fixture_dir):
    """Az IG-posztok elérése nem nulla, hanem ismeretlen.

    Ha beleszámítanának az átlagba, az organikus átlagelérés 130-ról 68-ra
    esne — csendben, minden teszt zöldje mellett.
    """
    data = build(fixture_dir, period="2026-07")
    cross = data["cross"]
    assert cross["posts_total"] == 31
    assert cross["posts_measured"] == 16
    assert cross["avg_reach_organic_post"] == 130
    assert cross["avg_reach_boosted_post"] == 4312
    assert cross["reach_multiplier"] == 33.2


def test_build_output_is_json_serialisable(fixture_dir):
    import json

    data = build(fixture_dir, period="2026-07")
    json.dumps(data, ensure_ascii=False)


def test_wrong_period_is_rejected(fixture_dir):
    with pytest.raises(PeriodMismatchError):
        build(fixture_dir, period="2026-06")


def test_foreign_client_is_rejected(fixture_dir, tmp_path):
    other = tmp_path / "mammut-2026-07"
    shutil.copytree(fixture_dir, other)
    config = yaml.safe_load((other / "client.yaml").read_text(encoding="utf-8"))
    config["client"]["fb_page_id"] = "999999"
    (other / "client.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(ClientMismatchError):
        build(other, period="2026-07")


def test_two_zoomsphere_exports_are_rejected(fixture_dir, tmp_path):
    """Újraletöltésnél a régi fájl bennmarad — enélkül az egyikük csendben elveszne."""
    other = tmp_path / "larus-2026-07"
    shutil.copytree(fixture_dir, other)
    original = next(other.glob("input/*Scheduler*.xlsx"))
    shutil.copy(original, original.with_name("export_masolat.xlsx"))
    with pytest.raises(DuplicateSourceError, match="ZoomSphere"):
        build(other, period="2026-07")


def test_two_ads_exports_are_rejected(fixture_dir, tmp_path):
    other = tmp_path / "larus-2026-07"
    shutil.copytree(fixture_dir, other)
    original = next(other.glob("input/*Kampányok*.csv"))
    shutil.copy(original, original.with_name("kampanyok_masolat.csv"))
    with pytest.raises(DuplicateSourceError, match="Meta Ads"):
        build(other, period="2026-07")


def test_several_daily_and_content_exports_are_allowed(fixture_dir):
    """Napi metrikából csempénként, Tartalomból csatornánként több fájl a normális."""
    data = build(fixture_dir, period="2026-07")
    assert set(data["channels"]) == {"facebook", "instagram"}


def test_two_content_exports_for_the_same_channel_are_rejected(fixture_dir, tmp_path):
    """A Meta ugyanarra a hónapra több Tartalom exportot is ad, eltérő fájlnévvel.

    Ha mindkettő a mappában marad, minden poszt kétszer kerülne be: az
    elérés-összegek és az átlagok csendben megduplázódnának.
    """
    other = tmp_path / "larus-2026-07"
    shutil.copytree(fixture_dir, other)
    original = next(other.glob("input/Jul-01-2026*.csv"))
    shutil.copy(original, original.with_name("Jul-01-2026_masodik_export.csv"))

    with pytest.raises(DuplicateSourceError, match="Tartalom export"):
        build(other, period="2026-07")


def test_two_content_exports_for_different_channels_are_allowed(fixture_dir, tmp_path):
    """Facebookra és Instagramra külön export jön — ez a normális eset."""
    data = build(fixture_dir, period="2026-07")
    assert data["quality"]["posts_measured"] == 16


def test_missing_sources_are_named_with_what_they_cost(fixture_dir):
    """A varázsló első lépése erre épül: nem elég tudni, hogy hiányzik —
    azt is meg kell mondani, mi vész el nélküle."""
    data = build(fixture_dir, period="2026-07")
    assert any("Instagram Tartalom" in gap for gap in data["missing"])
    assert all("—" in gap for gap in data["missing"]), "mindegyik mondja meg, mibe kerül"


def test_a_complete_folder_reports_nothing_missing(fixture_dir, tmp_path):
    import shutil

    work = tmp_path / "teljes"
    shutil.copytree(fixture_dir, work)
    original = next(work.glob("input/Jul-01-2026*.csv"))
    # az IG Tartalom export pótlása: elég, hogy a csatorna jelen legyen
    faked = original.read_text(encoding="utf-8-sig").replace(
        "facebook.com", "instagram.com"
    )
    original.with_name("Jul-01-2026_instagram.csv").write_text(faked, encoding="utf-8")

    assert build(work, period="2026-07")["missing"] == []


def test_an_empty_input_folder_is_an_error_not_a_zero_report(fixture_dir, tmp_path):
    """Üres mappával csendben nullákkal teli riport készült volna."""
    import shutil

    work = tmp_path / "ures"
    shutil.copytree(fixture_dir, work)
    for path in (work / "input").iterdir():
        path.unlink()

    with pytest.raises(NoSourceError, match="egyetlen felismerhető forrásfájl sincs"):
        build(work, period="2026-07")


def test_a_channel_the_client_does_not_have_is_not_reported_missing(
    fixture_dir, tmp_path
):
    """Csak arról hiányolunk adatot, amiről a client.yaml szerint van fiók."""
    import shutil

    import yaml as yaml_module

    work = tmp_path / "csak_fb"
    shutil.copytree(fixture_dir, work)
    config = yaml_module.safe_load((work / "client.yaml").read_text(encoding="utf-8"))
    del config["client"]["ig_handle"]
    (work / "client.yaml").write_text(
        yaml_module.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )

    gaps = build(work, period="2026-07")["missing"]
    assert not any("Instagram" in gap for gap in gaps)


def test_a_new_client_gets_a_template_not_a_traceback(tmp_path):
    """Egy új ügyfélnél a client.yaml még nincs meg — ez az első parancs,
    amit a menedzser lefuttat, és eddig nyers FileNotFoundError volt."""
    (tmp_path / "input").mkdir()

    with pytest.raises(MissingConfigError) as caught:
        build(tmp_path, period="2026-07")

    message = str(caught.value)
    assert "client.yaml" in message
    assert "fb_page_id" in message, "a sablon legyen benne, ne csak a hiány ténye"
    assert "ig_handle" in message


def test_the_template_is_filled_in_from_the_exports(fixture_dir, tmp_path):
    """Az oldalazonosító ott van a Tartalom exportban. Bekérni olyasmit, amit
    már megkaptunk, elakasztja azt a menedzsert, aki nem éri el a Business
    Suite-ot — és pont ő a leggyakoribb eset."""
    work = tmp_path / "uj"
    shutil.copytree(fixture_dir, work)
    (work / "client.yaml").unlink()

    with pytest.raises(MissingConfigError) as caught:
        build(work, period="2026-07")

    message = str(caught.value)
    assert '"100064824963030"' in message, "az oldalazonosító a Tartalom exportból"
    assert '"Larus Étterem"' in message, "az oldal neve ugyanonnan"
    assert "currency: EUR" in message, "a pénznem a Meta Ads export fejlécéből"
    # amit tényleg nem tudunk, az placeholder marad — nem találjuk ki
    assert "<instagram felhasználónév" in message

    # és amit kiír, az érvényes YAML, egy másolással használható
    template = message.split("\n\n", 1)[1]
    assert yaml.safe_load(template)["client"]["fb_page_id"] == "100064824963030"
