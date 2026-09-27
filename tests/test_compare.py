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


def _work_copy(tmp_path):
    """A fixture munkapéldánya: a teszt írhat bele review.json-t és
    previous.json-t anélkül, hogy a fixture-höz nyúlna."""
    import shutil
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "larus-2026-07"
    work = tmp_path / "larus" / "2026-07"
    shutil.copytree(fixture, work)
    (work / "report_data.golden.json").unlink()
    return work


def test_a_partial_fill_leaves_the_rest_fillable(tmp_path):
    """Aki az első körben csak egy előző havi számot ír be, a többit a
    következő riportban is be tudja írni.

    Korábban a mezők csak a teljesen üres csatornán jelentek meg: egyetlen
    beírt érték után a csatorna többi mezője eltűnt, és a riportból többé nem
    volt pótolható.
    """
    from pipeline.build import build
    from pipeline.render import render

    work = _work_copy(tmp_path)
    (work / "review.json").write_text(
        json.dumps({"manual": {"prev_facebook_visits": 1400}}), encoding="utf-8"
    )
    data = build(work, "2026-07")
    assert data["comparison"]["facebook"]["visits"]["before"] == 1400

    html = render(
        data, cache_dir=tmp_path / "cache", fetcher=lambda url: b"", manual=data["manual"]
    )
    assert 'data-manual="prev_facebook_visits"' not in html, "ez már kész kártya"
    for key in ("link_clicks", "interactions", "follows"):
        assert f'data-manual="prev_facebook_{key}"' in html
    assert html.count('class="page manual-only-page"') == 1, "csak az Instagram-oldal üres"


def test_a_manual_value_fills_only_what_the_previous_report_lacks(tmp_path):
    """Az előző havi riport az erősebb forrás. A kézi érték csak azt pótolja,
    ami abból hiányzik — erre a metrikára a riport kitölthető mezőt mutat, és
    annak hatnia kell. Korábban previous.json mellett a kézi értéket meg sem
    nézte."""
    from pipeline.build import build

    work = _work_copy(tmp_path)
    (work / "previous.json").write_text(
        json.dumps(
            {
                "meta": {"period": "2026-06"},
                "channels": {"facebook": {"totals": {"visits": 1000}}},
            }
        ),
        encoding="utf-8",
    )
    (work / "review.json").write_text(
        json.dumps(
            {"manual": {"prev_facebook_visits": 1, "prev_facebook_link_clicks": 900}}
        ),
        encoding="utf-8",
    )
    facebook = build(work, "2026-07")["comparison"]["facebook"]
    assert facebook["visits"]["before"] == 1000, "az előző havi riport nyer"
    assert facebook["link_clicks"]["before"] == 900, "a kézi érték a hiányt pótolja"
