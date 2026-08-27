from datetime import date

import pytest

from pipeline.errors import MeasurementPeriodError
from pipeline.periods import (
    continuity,
    filter_daily,
    filter_items,
    filter_posts,
    require_complete_daily,
    resolve_period,
)
from pipeline.schema import ContentItem, DailySeries, Post


def test_manager_dates_win_and_period_uses_the_closing_month():
    resolved = resolve_period(
        label="2026-06",
        manager_start="2026-06-25",
        manager_end="2026-07-24",
        daily_windows=[(date(2026, 7, 1), date(2026, 7, 31))],
        ads_window=(date(2026, 6, 1), date(2026, 7, 31)),
    )

    assert resolved.start == date(2026, 6, 25)
    assert resolved.end == date(2026, 7, 24)
    assert resolved.label == "2026-07"
    assert resolved.source == "manager"
    assert resolved.credibility == "first_baseline"


def test_missing_dates_fall_back_to_common_daily_window_then_ads_then_calendar():
    daily = resolve_period(
        "2026-07",
        None,
        None,
        [
            (date(2026, 6, 24), date(2026, 7, 25)),
            (date(2026, 6, 25), date(2026, 7, 24)),
        ],
        (date(2026, 6, 1), date(2026, 7, 31)),
    )
    assert (daily.source, daily.start, daily.end) == (
        "daily_exports",
        date(2026, 6, 25),
        date(2026, 7, 24),
    )

    ads = resolve_period(
        "2026-07",
        None,
        None,
        [],
        (date(2026, 6, 25), date(2026, 7, 24)),
    )
    assert ads.source == "meta_ads"

    assumed = resolve_period("2026-07", None, None, [], None)
    assert (assumed.start, assumed.end, assumed.source, assumed.credibility) == (
        date(2026, 7, 1),
        date(2026, 7, 31),
        "calendar_fallback",
        "assumed",
    )


def test_one_sided_manager_input_is_ignored_in_favour_of_source_evidence():
    resolved = resolve_period(
        "2026-07",
        "2026-06-25",
        None,
        [(date(2026, 7, 1), date(2026, 7, 31))],
        None,
    )

    assert (resolved.start, resolved.end, resolved.source) == (
        date(2026, 7, 1),
        date(2026, 7, 31),
        "daily_exports",
    )


def test_reversed_manager_dates_are_rejected():
    with pytest.raises(MeasurementPeriodError, match="záródátum"):
        resolve_period("2026-07", "2026-07-24", "2026-06-25", [], None)


def test_contiguous_period_starts_after_previous_end():
    found = continuity(
        date(2026, 7, 25), date(2026, 8, 24), date(2026, 7, 24)
    )

    assert found == {
        "status": "continuous",
        "duration_days": 31,
        "gap_days": 0,
        "overlap_days": 0,
    }


@pytest.mark.parametrize(
    ("start", "end", "previous_end", "expected"),
    [
        (date(2026, 7, 27), date(2026, 8, 24), date(2026, 7, 24), "gap"),
        (date(2026, 7, 24), date(2026, 8, 24), date(2026, 7, 24), "overlap"),
        (date(2026, 7, 25), date(2026, 8, 5), None, "nonstandard"),
        (date(2026, 7, 25), date(2026, 8, 24), None, "first_baseline"),
    ],
)
def test_gap_overlap_first_and_nonstandard_are_distinct(
    start, end, previous_end, expected
):
    assert continuity(start, end, previous_end)["status"] == expected


def test_daily_filter_is_inclusive_and_returns_a_new_series():
    original = DailySeries(
        channel="facebook",
        field="visits",
        metric="Facebook-felkeresések",
        points=[
            (date(2026, 6, 24), 1),
            (date(2026, 6, 25), 2),
            (date(2026, 7, 24), 3),
            (date(2026, 7, 25), 4),
        ],
    )

    filtered = filter_daily(original, date(2026, 6, 25), date(2026, 7, 24))

    assert filtered.points == [
        (date(2026, 6, 25), 2),
        (date(2026, 7, 24), 3),
    ]
    assert original.points[0][0] == date(2026, 6, 24)
    assert filtered is not original


def test_instagram_follows_filter_fills_meta_omitted_zero_days():
    series = DailySeries(
        channel="instagram",
        field="follows",
        metric="Instagram-követések",
        points=[
            (date(2026, 7, 26), 3),
            (date(2026, 7, 28), 2),
        ],
    )

    filtered = filter_daily(series, date(2026, 7, 25), date(2026, 7, 28))

    assert filtered.points == [
        (date(2026, 7, 25), 0),
        (date(2026, 7, 26), 3),
        (date(2026, 7, 27), 0),
        (date(2026, 7, 28), 2),
    ]
    require_complete_daily(filtered, date(2026, 7, 25), date(2026, 7, 28))


def test_daily_completeness_names_metric_and_every_missing_day():
    series = DailySeries(
        channel="instagram",
        field="visits",
        metric="Instagram-felkeresések",
        points=[
            (date(2026, 7, 1), 1),
            (date(2026, 7, 2), 1),
            (date(2026, 7, 4), 1),
        ],
    )

    with pytest.raises(MeasurementPeriodError) as caught:
        require_complete_daily(series, date(2026, 7, 1), date(2026, 7, 5))

    assert "Instagram-felkeresések" in str(caught.value)
    assert "2026-07-03" in str(caught.value)
    assert "2026-07-05" in str(caught.value)


def test_sparse_content_is_filtered_without_requiring_boundary_posts():
    posts = [
        Post("facebook", "before", date(2026, 6, 24)),
        Post("facebook", "inside", date(2026, 7, 10)),
        Post("facebook", "after", date(2026, 7, 25)),
    ]
    items = [
        ContentItem(date(2026, 6, 24), "image"),
        ContentItem(date(2026, 7, 20), "reel"),
        ContentItem(date(2026, 7, 25), "story"),
    ]

    assert [post.post_id for post in filter_posts(
        posts, date(2026, 6, 25), date(2026, 7, 24)
    )] == ["inside"]
    assert [item.post_type for item in filter_items(
        items, date(2026, 6, 25), date(2026, 7, 24)
    )] == ["reel"]


def test_yaml_dates_arrive_as_date_objects_not_strings():
    """A `client.yaml`-ben idézőjel nélkül álló dátumot a YAML dátummá alakítja.

    Az éles Mammut-generálás ezen állt meg: a webes felület
    `measurement_start: 2026-07-25` alakban írta ki, a PyYAML `datetime.date`-et
    adott vissza, a `date.fromisoformat` pedig sztringet vár. A menedzser kézzel
    szerkesztett fájljában ugyanígy előfordulhat — a motornak el kell fogadnia.
    """
    from datetime import date

    from pipeline.periods import _parse_date

    assert _parse_date("2026-07-25", "mérés kezdete") == date(2026, 7, 25)
    assert _parse_date(date(2026, 7, 25), "mérés kezdete") == date(2026, 7, 25)


def test_a_real_wrong_value_still_fails():
    """A tűrés nem jelenti azt, hogy bármit elfogadunk."""
    import pytest

    from pipeline.errors import MeasurementPeriodError
    from pipeline.periods import _parse_date

    with pytest.raises(MeasurementPeriodError, match="YYYY-MM-DD"):
        _parse_date("2026.07.25", "mérés kezdete")
    with pytest.raises(MeasurementPeriodError, match="YYYY-MM-DD"):
        _parse_date(None, "mérés kezdete")
