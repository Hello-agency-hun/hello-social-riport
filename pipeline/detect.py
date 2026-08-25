from dataclasses import dataclass
from pathlib import Path
import re

from pipeline.tabular import read_table_header, table_format
from pipeline.textio import read_lines

DAILY_METRICS = {
    "Facebook-felkeresések": ("facebook", "visits"),
    "Facebook-követések": ("facebook", "follows"),
    "Tartalomnál végzett műveletek": ("facebook", "interactions"),
    "Facebookos hivatkozáskattintások": ("facebook", "link_clicks"),
    "Instagram-profilfelkeresések": ("instagram", "visits"),
    "Instagramos hivatkozáskattintások": ("instagram", "link_clicks"),
    "Interakció tartalmaknál": ("instagram", "interactions"),
    # A Mammut-próbán derült ki, hogy ez a csempe létezik. Addig a rendszer
    # kézi override-ot kért rá, a README pedig azt állította, hogy Instagramon
    # „nincs napi követés-csempe" — ezért a követőszám-lánc ott sosem indult el.
    "Instagram-követések": ("instagram", "follows"),
}

# Napi elérés-csempék. NEM hiba, ha bekerülnek — logikus, hogy a menedzser
# letölti őket, hiszen a havi eléréshez pont ezt a csempét kell megnyitni.
# Forrásként viszont használhatatlanok: a napi elérés nem összegezhető, mert
# aki két napon látott minket, egy ember. A havi számot a csempe fejlécéről
# kell leolvasni. Ezért felismerjük és szelíden elutasítjuk, nem hibázunk
# rajtuk egy értelmezhetetlen mezőnév-listával.
DAILY_REACH_TILES = {
    "Nézők",
    "Elérés",
    "Facebook-nézők",
    "Instagram-elérés",
    "Facebook-elérés",
    "Instagram-nézők",
}


@dataclass
class Source:
    path: Path
    kind: str
    metric: str | None = None
    channel: str | None = None
    field: str | None = None
    adaptation: str | None = None


# A mappába nem csak az kerül, amit kérünk. A menedzser letölti rossz
# formátumban, vagy bedobja a Business Suite képernyőképeit is. Egyik sem hiba —
# csak tudnunk kell, mi az, hogy értelmesen tudjunk szólni róla.
SIGNATURES = [
    (b"%PDF", "pdf"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "legacy_office"),  # régi .xls/.doc
    (b"\x89PNG\r\n\x1a\n", "screenshot"),
    (b"\xff\xd8\xff", "screenshot"),
    (b"GIF8", "screenshot"),
    (b"RIFF", "screenshot"),  # webp
]


def sniff(path: Path) -> str | None:
    """A fájl típusa a tartalma első bájtjaiból — a kiterjesztés hazudhat."""
    try:
        head = Path(path).open("rb").read(8)
    except OSError:
        return None
    for magic, kind in SIGNATURES:
        if head.startswith(magic):
            return kind
    return None


def identify(path: Path) -> Source:
    path = Path(path)

    sniffed = sniff(path)
    if sniffed in {"pdf", "screenshot"}:
        return Source(path, sniffed)

    # A napi csempék speciális, kétsoros fejléce megelőzi a normál táblázatot.
    # Bináris Excelt nem próbálunk szövegként dekódolni.
    actual_format = table_format(path)
    if actual_format == "csv":
        lines = read_lines(path)
        if lines and lines[0].lower().startswith("sep="):
            metric = lines[1].strip().strip('"') if len(lines) > 1 else ""
            channel, field = DAILY_METRICS.get(metric, (None, None))
            return Source(path, "meta_daily", metric=metric, channel=channel, field=field)

    try:
        header = set(read_table_header(path))
    except Exception:
        if sniffed == "legacy_office":
            return Source(path, "legacy_office")
        if actual_format == "xlsx":
            return Source(path, "spreadsheet")
        return Source(path, "unknown")

    from pipeline.parsers.meta_ads import REQUIRED as ADS_REQUIRED
    from pipeline.parsers.meta_content import REQUIRED as CONTENT_REQUIRED
    from pipeline.parsers.zoomsphere import REQUIRED_HEADERS as ZOOMSPHERE_REQUIRED

    adaptation = None if actual_format == "csv" else actual_format.upper()
    if ZOOMSPHERE_REQUIRED.issubset(header):
        return Source(
            path,
            "zoomsphere",
            adaptation=None if actual_format == "xlsx" else actual_format.upper(),
        )
    # Egy sérült fejléc miatt se essen vissza „ismeretlenre” az egész export.
    # Három együttes Meta-oszlop már elég erős ujjlenyomat; a parser ezután
    # pontosan megnevezi, melyik kötelező oszlop hiányzik.
    if len(set(ADS_REQUIRED) & header) >= 3 or "Kampány neve" in header:
        return Source(path, "meta_ads", adaptation=adaptation)
    if len(set(CONTENT_REQUIRED) & header) >= 3 or "Bejegyzésazonosító" in header:
        return Source(path, "meta_content", adaptation=adaptation)

    if actual_format == "xlsx":
        return Source(path, "spreadsheet")
    if actual_format == "xls":
        return Source(path, "legacy_office")

    return Source(path, "unknown")


def _canonical_upload_name(path: Path) -> tuple[str, str]:
    """Collapse the suffix added by browsers/hosting for a repeated upload."""
    stem = re.sub(r"(?:\s+-\s*\d+|\s*\(\d+\))$", "", path.stem).strip().rstrip(".")
    return stem.casefold(), path.suffix.casefold()


def scan(directory: Path) -> list[Source]:
    sources = [identify(p) for p in sorted(Path(directory).iterdir()) if p.is_file()]
    recognized_names = {
        _canonical_upload_name(source.path)
        for source in sources
        if source.kind != "unknown"
    }
    for source in sources:
        if (
            source.kind == "unknown"
            and _canonical_upload_name(source.path) in recognized_names
        ):
            source.kind = "ignored_duplicate"
    return sources
