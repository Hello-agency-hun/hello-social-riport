import csv
from datetime import datetime

from pipeline.detect import DAILY_METRICS
from pipeline.errors import MissingColumnError, UnknownSourceError
from pipeline.labels import PAGE_FIELDS
from pipeline.schema import DailySeries, ParsedSource
from pipeline.textio import read_lines


def _unknown_metric_help(path, metric: str) -> str:
    """A hiba önmagában nem segítség.

    Az üzenet eddig annyit mondott, hogy „add hozzá a `daily_metric_overrides`
    szakaszhoz" — se formátumot, se választható mezőneveket nem mutatott. A
    csempék közül ez az egyetlen fajta, ami nem árulja el a csatornáját, tehát
    a menedzser pont ott marad magára, ahol a legkevesebb támpontja van.
    """
    # A csempe magyar neve megmondja, melyik mezőről van szó — a riport ugyanezt
    # a szótárat használja visszafelé, a feliratokhoz.
    field = {label: key for key, label in PAGE_FIELDS.items()}.get(metric, "<mező>")
    # A csatornát nem tippeljük meg a nevéből, ha nincs benne. Egy rossz tipp itt
    # nem hibát okoz, hanem csendben a másik csatorna grafikonjára teszi a görbét.
    known = (
        "instagram" if "nstagram" in metric
        else "facebook" if "acebook" in metric
        else None
    )
    hint = "" if known else '   # vagy "instagram" — ez a csempe nem árulja el'

    return (
        f"{path}: a(z) {metric!r} csempe nem árulja el, melyik csatornáé.\n"
        "Nézd meg, a Business Suite → Eredmények melyik fülén töltötted le, és "
        "másold a client.yaml végére:\n\n"
        "daily_metric_overrides:\n"
        f'  "{metric}": ["{known or "facebook"}", "{field}"]{hint}\n\n'
        f"Választható mezőnevek: {', '.join(sorted(PAGE_FIELDS))}"
    )


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
        raise UnknownSourceError(_unknown_metric_help(path, metric))
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
