"""Egységes táblázat-beolvasás, a fájlnévtől és kiterjesztéstől függetlenül."""

from datetime import date, datetime
from pathlib import Path
import re
import zipfile

from pipeline.textio import read_csv_header, read_csv_rows

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# Ezres tagolásra használt szóközfélék: sima, nem törhető és keskeny szóköz.
_GROUPING = re.compile(r"[\s  ']")
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


def parse_number(value) -> float | None:
    """Szám a cellából — akárhogy mentette el a menedzser.

    A Meta nyers exportja `1234.5` alakú, de ha a menedzser megnyitja és
    elmenti magyar Excelben, pontosvesszős CSV lesz belőle `1 234,5`
    alakú számokkal. A pontosvesszőt már felismertük, a tizedesvesszőt nem:
    a `float("13,90")` hibát dobott, a parser nullát írt helyette, és a
    költés + megjelenés nulla sorokat „nullás kampányként” csendben kiszűrtük.
    Egy egész hónap hirdetése tűnt volna el hibaüzenet nélkül.

    Elfogadott alakok: `1234.5`, `1 234,5`, `1,234.5`, `1.234,5`, `13,90`,
    `−87`, `12%`. Egyetlen vessző tizedesjel (a magyar Excel így ment);
    több vessző ezres tagolás. `None`, ha a cella üres vagy nem szám
    (`N/A`, `–`) — azt a hívó dönti el, mit jelent.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _GROUPING.sub("", str(value)).replace("−", "-").rstrip("%")
    if not text:
        return None
    if "," in text and "." in text:
        # Amelyik később jön, az a tizedesjel: `1.234,5` vagy `1,234.5`.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif text.count(",") == 1:
        text = text.replace(",", ".")
    elif text.count(",") > 1:
        text = text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    if not _NUMBER.fullmatch(text):
        return None
    return float(text)


# A dátumcellák alakjai. A sorrend számít: az ISO előbb jön, mert egyértelmű;
# a `07/01/2026` a Meta saját (amerikai) formátuma, a `2026. 07. 01.` pedig
# az, amit a magyar Excel ír vissza mentéskor. Nap-hónap sorrendű alakot
# (`01.07.2026`) szándékosan nem fogadunk el: a `07/01` és az `01.07`
# ugyanazt a napot más hónapba tenné, és ezt semmi nem jelezné.
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%Y. %m. %d.",
    "%Y. %m. %d. %H:%M",
    "%Y. %m. %d. %H:%M:%S",
    "%Y.%m.%d.",
    "%Y.%m.%d",
    "%Y.%m.%d. %H:%M",
    "%Y.%m.%d %H:%M",
)


def parse_date(value) -> date | None:
    """Dátum a cellából, a Meta és a magyar Excel alakjaiban. `None`, ha nem az."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = " ".join(str(value or "").split())
    if not text:
        return None
    for pattern in _DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%m/%d/%Y %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _records(rows) -> list[dict[str, str]]:
    materialized = list(rows)
    if not materialized:
        return []
    header = [_text(value).strip().lstrip("\ufeff") for value in materialized[0]]
    if not any(header):
        return []
    return [
        {column: _text(value) for column, value in zip(header, row)}
        for row in materialized[1:]
        if any(_text(value).strip() for value in row)
    ]


def _xlsx_rows(path: Path) -> list[dict[str, str]]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            records = _records(sheet.iter_rows(values_only=True))
            if records:
                return records
        return []
    finally:
        workbook.close()


def _xls_rows(path: Path) -> list[dict[str, str]]:
    import xlrd

    workbook = xlrd.open_workbook(str(path), on_demand=True)
    try:
        for sheet in workbook.sheets():
            records = _records(sheet.row_values(index) for index in range(sheet.nrows))
            if records:
                return records
        return []
    finally:
        workbook.release_resources()


def table_format(path: Path) -> str:
    """A tényleges táblázatformátum; a kiterjesztés csak támpont."""
    path = Path(path)
    with path.open("rb") as stream:
        head = stream.read(8)
    if head.startswith(OLE_MAGIC):
        return "xls"
    if zipfile.is_zipfile(path):
        return "xlsx"
    return "csv"


def read_table_rows(path: Path) -> list[dict[str, str]]:
    """CSV, XLSX vagy XLS első nem üres munkalapja szótársorokként."""
    actual = table_format(path)
    if actual == "xlsx":
        return _xlsx_rows(path)
    if actual == "xls":
        return _xls_rows(path)
    return read_csv_rows(path)


def read_table_header(path: Path) -> list[str]:
    path = Path(path)
    actual = table_format(path)
    if actual == "csv":
        return read_csv_header(path)
    rows = read_table_rows(path)
    if rows:
        return list(rows[0])

    # A fejléc önmagában is elég a forrástípus felismeréséhez. Az üres export
    # később a parserben kap pontos, emberi hibaüzenetet.
    if actual == "xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet in workbook.worksheets:
                row = next(sheet.iter_rows(values_only=True), ())
                header = [_text(value).strip().lstrip("\ufeff") for value in row]
                if any(header):
                    return header
        finally:
            workbook.close()
    elif actual == "xls":
        import xlrd

        workbook = xlrd.open_workbook(str(path), on_demand=True)
        try:
            for sheet in workbook.sheets():
                if sheet.nrows:
                    header = [_text(value).strip().lstrip("\ufeff") for value in sheet.row_values(0)]
                    if any(header):
                        return header
        finally:
            workbook.release_resources()
    return []
