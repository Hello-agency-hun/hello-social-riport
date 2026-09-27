"""Öngyógyító bemeneti csomagok a riportmotorhoz."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import zipfile

from pipeline.tabular import table_format


MAX_FILES = 120
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 200 * 1024 * 1024


def _safe_stem(name: str) -> str:
    stem = Path(name.replace("\\", "/")).stem
    clean = re.sub(r"[^\w .()\-]+", "-", stem, flags=re.UNICODE).strip(" .-")
    return clean or "import"


def _text_table(data: bytes) -> bool:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True
    head = data[:65536]
    return b"\n" in head and any(mark in head for mark in (b",", b";", b"\t", b"sep="))


def _actual_suffix(temp: Path, original: str) -> str | None:
    with temp.open("rb") as stream:
        data = stream.read(65536)
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF8"):
        return ".gif"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return ".webp"
    actual = table_format(temp)
    if actual == "xlsx":
        return ".xlsx"
    if actual == "xls":
        return ".xls"
    if _text_table(data):
        return ".csv"
    suffix = Path(original).suffix.casefold()
    if suffix == ".json":
        return ".json"
    return None


def _unique_target(directory: Path, name: str, data: bytes) -> Path | None:
    target = directory / name
    if target.exists() and target.read_bytes() == data:
        return None
    counter = 2
    while target.exists():
        target = directory / f"{Path(name).stem} ({counter}){Path(name).suffix}"
        if target.exists() and target.read_bytes() == data:
            return None
        counter += 1
    return target


def expand_bundles(directory: Path) -> list[Path]:
    """A ZIP exportcsomagokat laposan, útvonalbejárás nélkül kibontja.

    XLSX maga is ZIP, ezért kizárólag a valódi, nem-workbook archívumok kerülnek
    ide. Ismételt futás idempotens: az azonos tartalom nem kap újabb másolatot.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []
    imported: list[Path] = []
    for bundle in sorted(directory.iterdir()):
        if not bundle.is_file() or bundle.suffix.casefold() != ".zip":
            continue
        if table_format(bundle) != "archive":
            continue
        with zipfile.ZipFile(bundle) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > MAX_FILES:
                raise ValueError(f"a ZIP túl sok fájlt tartalmaz ({len(infos)} > {MAX_FILES})")
            total = 0
            for info in infos:
                normalized = info.filename.replace("\\", "/")
                if "__MACOSX/" in normalized or Path(normalized).name == ".DS_Store":
                    continue
                total += info.file_size
                if info.file_size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                    raise ValueError("a ZIP kibontva túl nagy")
                data = archive.read(info)
                probe = directory / f".hello-import-{hashlib.sha256(data).hexdigest()[:12]}"
                probe.write_bytes(data)
                try:
                    suffix = _actual_suffix(probe, normalized)
                finally:
                    probe.unlink(missing_ok=True)
                if suffix is None:
                    continue
                target = _unique_target(directory, _safe_stem(normalized) + suffix, data)
                if target is None:
                    continue
                target.write_bytes(data)
                imported.append(target)
    return imported
