"""Előző havi riport számainak kinyerése PDF-ből — javaslatként.

Az első hónapban nincs `previous.json`, csak a korábbi riport PDF-je. Ebből ki
lehet olvasni a kulcsszámokat, de **nem megbízhatóan**: idegen elrendezés és
`149.3K` alakú kerekítés. Ezért a script nem ír `previous.json`-t, hanem
**javaslatot nyomtat**, amit a menedzser ellenőriz és beír a riport kézi mezőibe.
A második hónaptól erre nincs szükség: az előző havi `report_data.json` pontos.

A párosítás **geometriai**, nem szövegsorrend alapú. Ezekben a riportokban a
felirat közvetlenül a szám alatt áll, viszont a szövegkinyerés a számokat és a
feliratokat külön csoportban adja vissza — sorrend alapján minden metrika
ugyanazt az értéket kapná.

Használat:
    python tools/import_previous.py "<elozo riport.pdf>"
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.textio import force_utf8_output  # noqa: E402

# Felirat-töredékek magyarul és angolul — a régi riportok mindkettőt használják.
LABELS = {
    "impressions": ("impression", "megjelenés", "megtekint"),
    "reach": ("reach", "elérés"),
    "interactions": ("interaction", "interakció"),
    "visits": ("visit", "felkeres"),
    "link_clicks": ("link click", "hivatkozáskattint"),
    "followers": ("follower", "követ"),
}

CHANNELS = {"instagram": "instagram", "facebook": "facebook"}

# A felirat a szám alatt áll, nagyjából azonos oszlopban. Ezek a határok a
# Mammut riport 1920×1080-as oldalain mérve.
MAX_BELOW = 200.0
MAX_SIDEWAYS = 140.0


def parse_compact_number(text: str) -> int | None:
    """`149.3K` → 149300. A szóközöket és a `+` előjelet előbb eltávolítja."""
    cleaned = re.sub(r"[\s ]", "", str(text)).lstrip("+")
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)([KkMm]?)", cleaned)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    scale = {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2).lower()]
    return int(round(value * scale))


def _metric_for(text: str) -> str | None:
    lowered = text.lower()
    for key, needles in LABELS.items():
        if any(needle in lowered for needle in needles):
            return key
    return None


def pair_numbers_with_labels(spans: list[tuple[float, float, str]]) -> dict[str, int]:
    """Minden számhoz a hozzá legközelebbi, alatta álló felirat.

    `spans` elemei `(x, y, szöveg)`. Ha egy metrikához több szám is illeszkedik,
    a közelebbi nyer — a távolabbit nem írjuk felül.
    """
    numbers = []
    labels = []
    for x, y, text in spans:
        value = parse_compact_number(text)
        if value is not None:
            # A `+200` a havi változás, nem az összlétszám — ugyanaz a felirat
            # („Followers") a riport két oldalán két különböző dolgot jelöl.
            numbers.append((x, y, value, text.strip().startswith("+")))
            continue
        metric = _metric_for(text)
        if metric:
            labels.append((x, y, metric))

    best: dict[str, tuple[float, int]] = {}
    for x, y, value, is_change in numbers:
        candidates = [
            (label_y - y, metric)
            for label_x, label_y, metric in labels
            if 0 < label_y - y <= MAX_BELOW and abs(label_x - x) <= MAX_SIDEWAYS
        ]
        if not candidates:
            continue
        distance, metric = min(candidates)
        if is_change:
            metric += "_change"
        if metric not in best or distance < best[metric][0]:
            best[metric] = (distance, value)

    return {metric: value for metric, (_, value) in best.items()}


def harvest(document) -> dict[str, dict[str, int]]:
    """Csatornánként a megtalált metrikák. A csatornát az oldal címe adja meg."""
    result: dict[str, dict[str, int]] = {}

    for page in document:
        spans = []
        channel = None
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    spans.append((span["bbox"][0], span["bbox"][1], text))
                    channel = channel or CHANNELS.get(text.lower())

        if not channel:
            continue
        found = pair_numbers_with_labels(spans)
        for metric, value in found.items():
            result.setdefault(channel, {}).setdefault(metric, value)

    return result


def main(pdf_path: Path) -> int:
    import pymupdf

    found = harvest(pymupdf.open(pdf_path))
    if not found:
        print(f"{pdf_path.name}: nem találtam felismerhető szám–felirat párt.")
        return 1

    print(f"{pdf_path.name} — javaslat, ELLENŐRIZD:\n")
    for channel, metrics in found.items():
        print(f"  {channel}")
        for metric, value in metrics.items():
            print(f"    {metric:14} {value:>10,}".replace(",", " "))
    print(
        "\nEzek kerekített értékek lehetnek (149.3K → 149 300), és idegen\n"
        "elrendezésnél félre is csúszhatnak. Vesd össze a PDF-fel, majd írd be\n"
        "őket a riport kézi mezőibe."
    )
    return 0


if __name__ == "__main__":
    force_utf8_output()
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
