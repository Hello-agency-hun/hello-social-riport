"""Kreatívok letöltése és beágyazása.

A kész riport egyetlen önálló HTML fájl: e-mailben küldhető, offline megnyitható,
és PDF-be nyomtatva is hibátlan. Ezért minden kép base64 data URI-ként kerül bele,
nem külső hivatkozásként.

A letöltések a hónap mappájában cache-elődnek, így az újrarenderelés (review-kör)
nem tölt le újra semmit.
"""

import base64
import hashlib
import io
from pathlib import Path
from typing import Callable

from PIL import Image

MAX_WIDTH = 480
QUALITY = 82
TIMEOUT = 30

# Semleges helyőrző, ha egy kép nem tölthető le. Szándékosan felismerhető:
# a riportban látszania kell, hogy itt kép lett volna.
PLACEHOLDER = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3">'
            '<rect width="4" height="3" fill="#E4E0D8"/>'
            '<text x="2" y="1.7" text-anchor="middle" font-size=".32" '
            'fill="#6B665D">kép nem elérhető</text></svg>'
        ).encode("utf-8")
    ).decode("ascii")
)


def fetch(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "hello-reporting"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def to_data_uri(raw: bytes, max_width: int = MAX_WIDTH) -> str:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if image.width > max_width:
        height = round(image.height * max_width / image.width)
        image = image.resize((max_width, height), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=QUALITY, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def embed(
    urls: list[str],
    cache_dir: Path,
    fetcher: Callable[[str], bytes] = fetch,
    max_width: int = MAX_WIDTH,
) -> list[str]:
    """Minden URL-ből data URI. Ami nem tölthető le, helyőrzőt kap."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    results = []

    for url in urls:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        cached = cache / f"{key}.txt"
        if cached.exists():
            results.append(cached.read_text(encoding="ascii"))
            continue
        try:
            uri = to_data_uri(fetcher(url), max_width=max_width)
        except Exception:
            results.append(PLACEHOLDER)
            continue
        cached.write_text(uri, encoding="ascii")
        results.append(uri)

    return results
