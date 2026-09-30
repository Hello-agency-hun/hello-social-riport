import csv
import io
import unicodedata
from pathlib import Path

from pipeline.errors import PipelineError

BOMS = {
    b"\xff\xfe\x00\x00": "utf-32",
    b"\x00\x00\xfe\xff": "utf-32",
    b"\xff\xfe": "utf-16",
    b"\xfe\xff": "utf-16",
    b"\xef\xbb\xbf": "utf-8-sig",
}


def detect_encoding(raw: bytes) -> str:
    """A Meta exportjai UTF-8, UTF-16 vagy magyar Windows-1250 fájlok."""
    for bom, encoding in BOMS.items():
        if raw.startswith(bom):
            return encoding
    sample = raw[:4096]
    if len(sample) >= 8:
        if sample[1::2].count(0) > len(sample[1::2]) * 0.6:
            return "utf-16-le"
        if sample[::2].count(0) > len(sample[::2]) * 0.6:
            return "utf-16-be"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return "cp1250"
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
    return raw.decode(detect_encoding(raw)).lstrip("\ufeff")


def read_lines(path: Path) -> list[str]:
    """Nem üres sorok listája — fájlazonosításhoz és a napi CSV-k fejlécéhez.

    Ne használd CSV-tartalom beolvasására: az üres sorok eldobása szétvágná az
    idézőjeles, több bekezdésre tagolt mezőket. Arra `read_csv_rows` való.
    """
    return [line for line in read_text(path).splitlines() if line.strip()]


def _csv_reader(path: Path):
    text = read_text(path).lstrip("\r\n \t")
    first_line, separator, remainder = text.partition("\n")
    declared = first_line.strip().lower()
    if declared.startswith("sep=") and len(declared) == 5 and separator:
        delimiter = declared[-1]
        text = remainder
    else:
        try:
            delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    header = [unicodedata.normalize("NFC", str(value or "").strip().lstrip("\ufeff")) for value in (reader.fieldnames or [])]
    named = [value for value in header if value]
    if len(named) != len(set(named)):
        raise PipelineError(f"{path}: ismétlődő CSV-oszlopnév; az oszlopok nem különböztethetők meg.")
    reader.fieldnames = header
    return reader


def read_csv_header(path: Path) -> list[str]:
    reader = _csv_reader(path)
    return [str(value or "").strip().lstrip("\ufeff") for value in (reader.fieldnames or [])]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """CSV sorok szótárként.

    A nyers szöveget adja a parsernek, nem előszűrt sorokat — így a több sorra
    tagolt kampánynevek és poszt-szövegek bekezdéshatárai megmaradnak.
    """
    reader = _csv_reader(path)
    result = []
    for row in reader:
        if None in row and any(str(value or "").strip() for value in row[None]):
            raise PipelineError(f"{path}: több cella van a(z) {reader.line_num}. sorban, mint a fejlécben. Ellenőrizd az elválasztót és az idézőjeleket.")
        if any(str(value or "").strip() for key, value in row.items() if key is not None):
            result.append({key: (value or "") for key, value in row.items() if key})
    return result
