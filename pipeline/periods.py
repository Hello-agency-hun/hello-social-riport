"""Exact, inclusive measurement-period resolution for every report."""

from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import date, timedelta

from pipeline.errors import MeasurementPeriodError
from pipeline.schema import ContentItem, DailySeries, Post


@dataclass(frozen=True)
class MeasurementPeriod:
    start: date
    end: date
    label: str
    source: str
    credibility: str


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise MeasurementPeriodError(
            f"A {field} csak YYYY-MM-DD formátumú dátum lehet: {value!r}."
        ) from exc


def _calendar_window(label: str) -> tuple[date, date]:
    try:
        year_text, month_text = label.split("-")
        year, month = int(year_text), int(month_text)
        if len(year_text) != 4 or len(month_text) != 2:
            raise ValueError
        last_day = monthrange(year, month)[1]
    except (AttributeError, TypeError, ValueError) as exc:
        raise MeasurementPeriodError(
            f"A riport hónapja csak YYYY-MM formátumú lehet: {label!r}."
        ) from exc
    return date(year, month, 1), date(year, month, last_day)


def continuity(start: date, end: date, previous_end: date | None) -> dict:
    """Describe interval credibility using inclusive day boundaries."""
    if end < start:
        raise MeasurementPeriodError(
            "A mérés záródátuma nem lehet korábbi a kezdődátumnál."
        )

    duration = (end - start).days + 1
    result = {
        "status": "first_baseline",
        "duration_days": duration,
        "gap_days": 0,
        "overlap_days": 0,
    }

    if duration < 27 or duration > 32:
        result["status"] = "nonstandard"
        return result
    if previous_end is None:
        return result

    boundary = (start - previous_end).days
    if boundary == 1:
        result["status"] = "continuous"
    elif boundary > 1:
        result["status"] = "gap"
        result["gap_days"] = boundary - 1
    else:
        result["status"] = "overlap"
        result["overlap_days"] = 1 - boundary
    return result


def resolve_period(
    label: str,
    manager_start: str | None,
    manager_end: str | None,
    daily_windows: list[tuple[date, date]],
    ads_window: tuple[date, date] | None,
    previous_end: date | None = None,
) -> MeasurementPeriod:
    """Resolve dates from the strongest complete source of evidence."""
    _calendar_window(label)  # Validate the archive label even if another source wins.

    if manager_start and manager_end:
        start = _parse_date(manager_start, "mérés kezdete")
        end = _parse_date(manager_end, "mérés záródátuma")
        source = "manager"
    elif daily_windows:
        start = max(window[0] for window in daily_windows)
        end = min(window[1] for window in daily_windows)
        source = "daily_exports"
    elif ads_window:
        start, end = ads_window
        source = "meta_ads"
    else:
        start, end = _calendar_window(label)
        source = "calendar_fallback"

    if end < start:
        raise MeasurementPeriodError(
            "A mérés záródátuma nem lehet korábbi a kezdődátumnál, illetve "
            "a napi exportoknak közös időszakot kell lefedniük."
        )

    credibility = continuity(start, end, previous_end)["status"]
    if source == "calendar_fallback":
        credibility = "assumed"

    return MeasurementPeriod(
        start=start,
        end=end,
        label=f"{end.year:04d}-{end.month:02d}",
        source=source,
        credibility=credibility,
    )


def filter_daily(series: DailySeries, start: date, end: date) -> DailySeries:
    """Return inclusive points and restore Meta's omitted Instagram zero days."""
    points = [point for point in series.points if start <= point[0] <= end]
    if series.channel == "instagram" and series.field == "follows":
        # A Meta az Instagram-követések CSV-jéből kihagyja azokat a napokat,
        # amelyeken nem érkezett új követés. Más napi csempék explicit nulla
        # sorokat adnak, ezért csak ennél az ismert sparse metrikánál biztonságos
        # a hiányzó dátumot nullaként visszaállítani.
        values = dict(points)
        points = []
        cursor = start
        while cursor <= end:
            points.append((cursor, values.get(cursor, 0)))
            cursor += timedelta(days=1)
    return replace(
        series,
        points=points,
    )


def require_complete_daily(series: DailySeries, start: date, end: date) -> None:
    """Reject a daily metric when any requested calendar day is absent."""
    present = {day for day, _ in series.points}
    missing: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor not in present:
            missing.append(cursor)
        cursor += timedelta(days=1)
    if missing:
        dates = ", ".join(day.isoformat() for day in missing)
        raise MeasurementPeriodError(
            f"{series.metric}: hiányzó napi adatok — {dates}. "
            "Töltsd le újra ezt a csempét a teljes mérési időszakra."
        )


def filter_posts(posts: list[Post], start: date, end: date) -> list[Post]:
    """Filter sparse Meta content rows; boundary-day posts are not required."""
    return [post for post in posts if start <= post.published <= end]


def filter_items(
    items: list[ContentItem], start: date, end: date
) -> list[ContentItem]:
    """Filter sparse scheduler rows; boundary-day posts are not required."""
    return [item for item in items if start <= item.published <= end]
