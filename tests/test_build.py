import shutil

import pytest
import yaml

from pipeline.build import build
from pipeline.errors import (
    ClientMismatchError,
    DuplicateSourceError,
    PeriodMismatchError,
)


def test_build_produces_report_data(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    assert data["meta"]["client"] == "Larus Étterem"
    assert data["meta"]["period"] == "2026-07"
    assert data["meta"]["currency"] == "EUR"


def test_build_includes_every_section(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    for key in ("content", "posts", "page", "paid", "cross"):
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
    assert set(data["page"]) == {"facebook", "instagram"}
