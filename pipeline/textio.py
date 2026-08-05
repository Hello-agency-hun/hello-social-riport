import csv
import io
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


def force_utf8_output() -> None:
    """A magyar Windows konzol alapértelmezése cp1250, ami sem az `⚠` jelet,
    sem több ékezetes karaktert nem tud kódolni. Enélkül minden parancssori
    eszközünk a kiírásnál elszállna — a CLI még azelőtt, hogy a riportadat
    megíródna. Ezért minden belépési pont ezzel kezd.
    """
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def read_text(path: Path) -> str:
    """A fájl teljes szövege, kódolástól függetlenül, változtatás nélkül."""
    raw = Path(path).read_bytes()
    return raw.decode(detect_encoding(raw))


def read_lines(path: Path) -> list[str]:
    """Nem üres sorok listája — fájlazonosításhoz és a napi CSV-k fejlécéhez.

    Ne használd CSV-tartalom beolvasására: az üres sorok eldobása szétvágná az
    idézőjeles, több bekezdésre tagolt mezőket. Arra `read_csv_rows` való.
    """
    return [line for line in read_text(path).splitlines() if line.strip()]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """CSV sorok szótárként.

    A nyers szöveget adja a parsernek, nem előszűrt sorokat — így a több sorra
    tagolt kampánynevek és poszt-szövegek bekezdéshatárai megmaradnak.
    """
    reader = csv.DictReader(io.StringIO(read_text(path), newline=""))
    return [{k: (v or "") for k, v in row.items()} for row in reader]
