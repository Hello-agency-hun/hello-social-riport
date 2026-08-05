import shutil

import pytest
import yaml

from pipeline.build import build
from pipeline.errors import ClientMismatchError, PeriodMismatchError


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
    assert quality["posts_with_creative"] == 15
    assert quality["dropped_zero_campaign_rows"] == 16
    # nincs IG Tartalom export a fixture-ben → a 4 IG boost jelentve, nem tippelve
    assert len(quality["unmatched_boosts"]) == 4


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
