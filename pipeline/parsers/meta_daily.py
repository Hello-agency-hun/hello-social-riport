import csv
from pathlib import Path

from pipeline.detect import DAILY_METRICS, DAILY_REACH_TILES
from pipeline.errors import (
    DailyReachNotUsable,
    MissingColumnError,
    UnknownSourceError,
)
from pipeline.labels import PAGE_FIELDS
from pipeline.schema import DailySeries, ParsedSource
from pipeline.tabular import parse_date, parse_number
from pipeline.textio import read_lines


def _unknown_metric_help(path, metric: str) -> str:
    """A hiba önmagában nem segítség.

    Az üzenet eddig annyit mondott, hogy „add hozzá a `daily_metric_overrides`
    szakaszhoz" — se formátumot, se választható mezőneveket nem mutatott. A
    csempék közül ez az egyetlen fajta, ami nem árulja el a csatornáját, tehát
    a menedzser pont ott marad magára, ahol a legkevesebb támpontja van.
    """
    # A csempe magyar neve megmondja, melyik mezőről van szó — a riport ugyanezt
    # a szótárat használja visszafelé, a feliratokhoz. A Business Suite magyar
    # felületű, tehát itt mindig a magyar címkékből fejtünk vissza, akkor is,
    # ha a riport angolul készül.
    legacy_aliases = {
        # A Meta régebbi exportja ezt Impressionsként adta, az új felületen
        # ugyanez Views / Megtekintések néven jelenik meg.
        "Megjelenések": "views",
    }
    field = legacy_aliases.get(metric) or {
        label: key for key, label in PAGE_FIELDS["hu"].items()
    }.get(metric, "<mező>")
    # A csatornát nem tippeljük meg a nevéből, ha nincs benne. Egy rossz tipp itt
    # nem hibát okoz, hanem csendben a másik csatorna grafikonjára teszi a görbét.
    known = (
        "instagram" if "nstagram" in metric
        else "facebook" if "acebook" in metric
        else None
    )
    hint = "" if known else '   # vagy "instagram" — ez a csempe nem árulja el'

    # A kulcs a fájl neve, nem a csempéé: ugyanaz a csempenév mindkét
    # csatornán előfordulhat, és akkor a névre kulcsolt beállítás a két
    # letöltés közül nem tudna választani.
    return (
        f"{path}: a(z) {metric!r} csempe nem árulja el, melyik csatornáé.\n"
        "Nézd meg, a Business Suite → Eredmények melyik fülén töltötted le, és "
        "másold a client.yaml végére:\n\n"
        "daily_metric_overrides:\n"
        f'  "{Path(path).name}": ["{known or "facebook"}", "{field}"]{hint}\n\n'
        f"Választható mezőnevek: {', '.join(sorted(PAGE_FIELDS['hu']))}\n"
        "(A kulcs lehet a csempe neve is, de ha ugyanaz a csempe mindkét "
        "csatornán szerepel, akkor csak a fájlnév különbözteti meg őket.)"
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

    # A csempenév nem mindig egyedi: a Mammutnál a `Megtekintések` csempe
    # mindkét csatornán ugyanígy hívják, tehát egyetlen névre kulcsolt
    # beállítás mindkét fájlt ugyanarra a csatornára tenné — az egyik görbe
    # csendben a másik alá kerülne. Ezért a fájlnév erősebb kulcs, mint a
    # csempenév: az különbözteti meg a két letöltést.
    resolved = lookup.get(Path(path).name) or lookup.get(metric)
    if resolved is None:
        if metric in DAILY_REACH_TILES:
            # Nem hiba, hanem fölösleg — és ezt meg kell mondani, nem
            # mezőnevekkel dobálózni.
            raise DailyReachNotUsable(
                f"{path}: a(z) {metric!r} napi csempéjére nincs szükség.\n"
                "A napi elérés nem összegezhető: aki két napon látott minket, "
                "egy ember, tehát a napok összege mindig több a valóságnál.\n"
                "A havi számot a csempe FEJLÉCÉRŐL olvasd le, és írd a "
                "client.yaml `monthly_reach` szakaszába.\n"
                "Ezt a fájlt vedd ki az input mappából."
            )
        raise UnknownSourceError(_unknown_metric_help(path, metric))
    channel, field = resolved

    points = []
    for row in csv.reader(lines[2:]):
        if len(row) < 2 or row[0].strip().strip('"') in ("", "Dátum"):
            continue
        raw_day = row[0].strip().strip('"')
        raw_value = row[1].strip().strip('"')
        day = parse_date(raw_day)
        # Üres érték nulla (a Meta így jelzi az eseménytelen napot); az
        # ezres tagolású `1 234` szám. Ami egyik sem, azon megállunk: egy
        # napi érték csendes nullázása a havi összeget hamisítaná meg.
        value = parse_number(raw_value) if raw_value else 0.0
        if day is None or value is None:
            raise MissingColumnError(
                f"{path}: értelmezhetetlen sor a(z) {metric!r} csempénél — {row!r}"
            )
        points.append((day, int(value)))

    if not points:
        raise MissingColumnError(f"{path}: a(z) {metric!r} csempe egyetlen napi sort sem tartalmaz")

    series = DailySeries(channel=channel, field=field, metric=metric, points=points)
    days = [day for day, _ in points]
    return ParsedSource(
        kind="meta_daily",
        period=(min(days), max(days)),
        payload=series,
    )
