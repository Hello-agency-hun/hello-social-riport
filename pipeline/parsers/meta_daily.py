import csv
from datetime import datetime

from pipeline.detect import DAILY_METRICS
from pipeline.errors import MissingColumnError, UnknownSourceError
from pipeline.schema import DailySeries, ParsedSource
from pipeline.textio import read_lines


def parse(path, overrides: dict[str, tuple[str, str]] | None = None) -> ParsedSource:
    """A metrika kilétét a 2. sor mondja meg, nem a fájlnév."""
    lines = read_lines(path)
    if len(lines) < 3:
        raise MissingColumnError(
            f"{path}: csonka napi export — {len(lines)} sor. Várt szerkezet: "
            "`sep=,`, metrikanév, `\"Dátum\",\"Primary\"`, majd napi sorok."
        )
    metric = lines[1].strip().strip('"')

    lookup = dict(DAILY_METRICS)
    lookup.update(overrides or {})
    if metric not in lookup:
        raise UnknownSourceError(
            f"{path}: ismeretlen napi metrika — {metric!r}. "
            "Add hozzá a client.yaml `daily_metric_overrides` szakaszához."
        )
    channel, field = lookup[metric]

    points = []
    for row in csv.reader(lines[2:]):
        if len(row) < 2 or row[0].strip().strip('"') in ("", "Dátum"):
            continue
        raw_day = row[0].strip().strip('"')
        try:
            day = datetime.strptime(raw_day, "%Y-%m-%dT%H:%M:%S").date()
            value = int(float(row[1].strip().strip('"') or 0))
        except ValueError as error:
            raise MissingColumnError(
                f"{path}: értelmezhetetlen sor a(z) {metric!r} csempénél — "
                f"{row!r} ({error})"
            ) from error
        points.append((day, value))

    if not points:
        raise MissingColumnError(f"{path}: a(z) {metric!r} csempe egyetlen napi sort sem tartalmaz")

    series = DailySeries(channel=channel, field=field, metric=metric, points=points)
    days = [day for day, _ in points]
    return ParsedSource(
        kind="meta_daily",
        period=(min(days), max(days)),
        payload=series,
    )
