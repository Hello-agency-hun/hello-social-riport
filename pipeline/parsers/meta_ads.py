import re
from dataclasses import dataclass, field
from datetime import date, datetime

from pipeline.errors import MissingColumnError
from pipeline.schema import Campaign, ParsedSource
from pipeline.textio import read_csv_rows

BOOST_PREFIXES = {"Instagram-bejegyzés:": "instagram", "Bejegyzés:": "facebook"}
REQUIRED = ["Kampány neve", "Eredmény jelzése", "Elérés", "Megjelenések"]


@dataclass
class AdsPayload:
    campaigns: list[Campaign] = field(default_factory=list)
    currency: str = "EUR"
    dropped_zero_rows: int = 0


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
    rows = read_csv_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Ads export")

    header = list(rows[0].keys())
    for column in REQUIRED:
        if column not in header:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")

    currency = detect_currency(header)
    spend_column = f"Elköltött összeg ({currency})"

    payload = AdsPayload(currency=currency)
    starts, ends = [], []

    for row in rows:
        starts.append(datetime.strptime(row["Jelentés kezdete"], "%Y-%m-%d").date())
        ends.append(datetime.strptime(row["Jelentés vége"], "%Y-%m-%d").date())

        spend = _number(row.get(spend_column, ""))
        impressions = int(_number(row.get("Megjelenések", "")))
        if spend == 0 and impressions == 0:
            payload.dropped_zero_rows += 1
            continue

        name = row["Kampány neve"].replace("\n", " ").strip()
        channel = _boost_channel(name)
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
            )
        )

    return ParsedSource(
        kind="meta_ads",
        period=(min(starts), max(ends)),
        payload=payload,
    )
