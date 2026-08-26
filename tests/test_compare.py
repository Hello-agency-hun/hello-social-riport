import json

from pipeline.compare import deltas, load_previous


def test_delta_is_absolute_and_relative():
    result = deltas({"visits": 1525, "follows": 5}, {"visits": 1000, "follows": 5})
    assert result["visits"] == {"now": 1525, "before": 1000, "diff": 525, "pct": 52.5}
    assert result["follows"]["pct"] == 0.0


def test_missing_previous_metric_is_omitted_not_zero():
    """Ha egy metrika nem volt az előző hónapban, nem írunk 0%-ot."""
    result = deltas({"visits": 100, "views": 50}, {"visits": 80})
    assert "views" not in result


def test_zero_before_yields_no_percentage():
    result = deltas({"visits": 100}, {"visits": 0})
    assert result["visits"]["diff"] == 100
    assert result["visits"]["pct"] is None


def test_load_previous_returns_none_when_absent(tmp_path):
    assert load_previous(tmp_path) is None


def test_load_previous_reads_the_json(tmp_path):
    (tmp_path / "previous.json").write_text(
        json.dumps({"channels": {"facebook": {"totals": {"visits": 9}}}}),
        encoding="utf-8",
    )
    assert load_previous(tmp_path)["channels"]["facebook"]["totals"]["visits"] == 9


def test_previous_values_can_come_from_manual_entry():
    """Az első hónapban nincs previous.json — a menedzser beírja a számokat."""
    from pipeline.compare import previous_from_manual

    manual = {"prev_facebook_visits": 1000, "prev_instagram_visits": 500}
    assert previous_from_manual(manual, "facebook", ["visits", "follows"]) == {
        "visits": 1000
    }


def test_comparison_page_offers_fillable_fields_without_previous_data(tmp_path):
    """Ha nincs előző havi adat, a lap nem marad üres: beírható mezőket mutat.

    Enélkül a menedzser sosem tudná meg, hogy egyáltalán van ilyen oldal.
    """
    import json
    from pathlib import Path

    from pipeline.render import render

    golden = (
        Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
    )
    data = json.loads(golden.read_text(encoding="utf-8"))
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    assert 'data-manual="prev_facebook_visits"' in html
    assert "Változás az előző hónaphoz" in html
    assert 'class="page manual-only-page"' in html
    assert ".manual-only-page { display: none !important; }" in html
