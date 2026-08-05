from pathlib import Path

BOMS = {
    b"\xff\xfe": "utf-16",
    b"\xfe\xff": "utf-16",
    b"\xef\xbb\xbf": "utf-8-sig",
}


def detect_encoding(raw: bytes) -> str:
    """A Meta exportjai vegyesen UTF-16 LE és UTF-8 BOM-osak."""
    for bom, encoding in BOMS.items():
        if raw.startswith(bom):
            return encoding
    return "utf-8"


def read_lines(path: Path) -> list[str]:
    """Nem üres sorok listája, kódolástól függetlenül."""
    raw = Path(path).read_bytes()
    text = raw.decode(detect_encoding(raw))
    return [line for line in text.splitlines() if line.strip()]


def read_csv_rows(path: Path, skip: int = 0) -> list[dict[str, str]]:
    """CSV sorok szótárként. `skip` a fejléc előtti sorokat hagyja ki."""
    import csv

    lines = read_lines(path)[skip:]
    return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(lines)]
