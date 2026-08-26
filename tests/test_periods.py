from datetime import date

import pytest

from pipeline.errors import MeasurementPeriodError
from pipeline.periods import continuity, resolve_period


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
