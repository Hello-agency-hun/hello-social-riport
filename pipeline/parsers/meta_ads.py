import re
from dataclasses import dataclass, field
from datetime import date, datetime

from pipeline.errors import MissingColumnError
from pipeline.schema import Campaign, ParsedSource
from pipeline.tabular import read_table_rows

BOOST_PREFIXES = {"Instagram-bejegyzés:": "instagram", "Bejegyzés:": "facebook"}
REQUIRED = ["Eredmény jelzése", "Elérés", "Megjelenések"]
NAME_COLUMNS = {
    "Kampány neve": "campaign",
    "Hirdetéssorozat neve": "adset",
    "Hirdetés neve": "ad",
}


@dataclass
class AdsPayload:
    campaigns: list[Campaign] = field(default_factory=list)
    currency: str = "EUR"
    dropped_zero_rows: int = 0
    source_level: str = "campaign"


def detect_currency(header: list[str]) -> str:
    for column in header:
        match = re.search(r"Elköltött összeg \(([A-Z]{3})\)", column)
        if match:
            return match.group(1)
    return "EUR"


def _number(value: str) -> float:
    value = (value or "").strip()
    try:
        return float(value)
    except ValueError:
        return 0.0


def _date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _first_date(row: dict[str, str], columns: tuple[str, ...]) -> date | None:
    for column in columns:
        found = _date(row.get(column, ""))
        if found is not None:
            return found
    return None


# A boost nevét a Meta a bejegyzés típusából állítja elő, de az ügyfelek egy
# része saját előtaggal nevezi a kampányait — a Mammut júliusi exportjában
# minden sor `Mammut_Bejegyzés: …` alakban jött. A sor elejéhez kötött
# felismerés ilyenkor egyetlen boostot sem talál, és a hirdetett posztok
# csendben kimaradnak a rangsorból. Az előtag határa marad kötelező, hogy egy
# prózai „…bejegyzés:” a kampánynév közepén ne váljon boosttá.
BOOST_PATTERN = re.compile(
    "(?:^|[_\\-—:/ ])(" + "|".join(re.escape(p) for p in BOOST_PREFIXES) + ")"
)


def _boost_channel(name: str) -> str | None:
    match = BOOST_PATTERN.search(name.strip())
    return BOOST_PREFIXES[match.group(1)] if match else None


def parse(path) -> ParsedSource:
    rows = read_table_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Ads export")

    header = list(rows[0].keys())
    for column in REQUIRED:
        if column not in header:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")
    name_column = next((column for column in NAME_COLUMNS if column in header), None)
    if name_column is None:
        raise MissingColumnError(
            f"{path}: hiányzó névoszlop — Kampány neve, Hirdetéssorozat neve "
            "vagy Hirdetés neve"
        )

    currency = detect_currency(header)
    spend_column = f"Elköltött összeg ({currency})"

    payload = AdsPayload(currency=currency, source_level=NAME_COLUMNS[name_column])
    starts, ends = [], []

    for row in rows:
        report_start = datetime.strptime(row["Jelentés kezdete"], "%Y-%m-%d").date()
        report_end = datetime.strptime(row["Jelentés vége"], "%Y-%m-%d").date()
        starts.append(report_start)
        ends.append(report_end)

        spend = _number(row.get(spend_column, ""))
        impressions = int(_number(row.get("Megjelenések", "")))
        if spend == 0 and impressions == 0:
            payload.dropped_zero_rows += 1
            continue

        name = row[name_column].replace("\n", " ").strip()
        channel = _boost_channel(name)
        end_text = str(row.get("Vége", "") or "").strip()
        normalized_end = end_text.casefold()
        ongoing = normalized_end in {"folyamatban", "ongoing", "in progress"}
        delivery_status = str(row.get("Kampány teljesítése", "") or "").strip().casefold()
        payload.campaigns.append(
            Campaign(
                name=name,
                spend=spend,
                currency=currency,
                reach=int(_number(row.get("Elérés", ""))),
                impressions=impressions,
                frequency=_number(row.get("Gyakoriság", "")),
                link_clicks=int(_number(row.get("Hivatkozáskattintások", ""))),
                results=int(_number(row.get("Eredmények", ""))),
                result_type=row.get("Eredmény jelzése", "").strip(),
                cost_per_result=_number(row.get("Eredményenkénti költség", "")),
                status=row.get("Kampány teljesítése", "").strip(),
                channel=channel,
                is_boost=channel is not None,
                start_date=_first_date(
                    row, ("Kezdés", "Indulás", "Kampány kezdete")
                ),
                end_date=None if ongoing else _date(end_text),
                is_ongoing=ongoing,
                delivery_status=delivery_status,
                report_start=report_start,
                report_end=report_end,
            )
        )

    return ParsedSource(
        kind="meta_ads",
        period=(min(starts), max(ends)),
        payload=payload,
    )
