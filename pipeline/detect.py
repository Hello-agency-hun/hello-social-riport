from dataclasses import dataclass
from pathlib import Path

from pipeline.textio import read_lines

DAILY_METRICS = {
    "Facebook-felkeresések": ("facebook", "visits"),
    "Facebook-követések": ("facebook", "follows"),
    "Tartalomnál végzett műveletek": ("facebook", "interactions"),
    "Facebookos hivatkozáskattintások": ("facebook", "link_clicks"),
    "Instagram-profilfelkeresések": ("instagram", "visits"),
    "Instagramos hivatkozáskattintások": ("instagram", "link_clicks"),
    "Interakció tartalmaknál": ("instagram", "interactions"),
}


@dataclass
class Source:
    path: Path
    kind: str
    metric: str | None = None
    channel: str | None = None
    field: str | None = None


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
    if sniffed:
        return Source(path, sniffed)

    if path.suffix.lower() == ".xlsx":
        from pipeline.parsers.zoomsphere import looks_like_zoomsphere

        if looks_like_zoomsphere(path):
            return Source(path, "zoomsphere")
        return Source(path, "unknown")

    lines = read_lines(path)
    if not lines:
        return Source(path, "unknown")

    if lines[0].lower().startswith("sep="):
        metric = lines[1].strip().strip('"')
        channel, field = DAILY_METRICS.get(metric, (None, None))
        return Source(path, "meta_daily", metric=metric, channel=channel, field=field)

    header = lines[0]
    if "Kampány neve" in header:
        return Source(path, "meta_ads")
    if "Bejegyzésazonosító" in header:
        return Source(path, "meta_content")

    return Source(path, "unknown")


def scan(directory: Path) -> list[Source]:
    return [identify(p) for p in sorted(Path(directory).iterdir()) if p.is_file()]
