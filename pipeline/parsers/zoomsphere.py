import zipfile
from pathlib import Path

REQUIRED_HEADERS = {"PostType", "FacebookPostIDs", "InstagramPostIDs"}


def looks_like_zoomsphere(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError):
        return False
    return all(header in sheet for header in REQUIRED_HEADERS)
