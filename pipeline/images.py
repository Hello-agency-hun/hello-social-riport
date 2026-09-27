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
import re
from concurrent.futures import ThreadPoolExecutor
from html import escape, unescape
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

MAX_WIDTH = 480
QUALITY = 82
TIMEOUT = 30
# Egyszerre ennyi kép töltődik. Korábban egyenként, egymás után mentek, és
# képenként 30 másodperces időkorláttal egy lassú CDN mellett a renderelés
# percekig tartott.
MAX_WORKERS = 8
# Az átlátszó képek (PNG-logók) háttere: a lap színe. A JPEG-be alakítás
# enélkül feketére festette az átlátszó részt.
PAPER = (255, 253, 249)

def placeholder(text: str = "kép nem elérhető") -> str:
    """Semleges helyőrző, ha egy kép nem tölthető le. Szándékosan
    felismerhető: a riportban látszania kell, hogy itt kép lett volna.

    A szöveg a riport nyelvén jön. A betűtípust ki kell mondani: a data URI-s
    SVG nem örökli a lap fontját, és alapértelmezésben talpas betűvel jelent
    meg — idegen testként a riport tipográfiájában.
    """
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3">'
        '<rect width="4" height="3" fill="#E4E0D8"/>'
        '<text x="2" y="1.62" text-anchor="middle" font-size=".2" '
        'font-family="Helvetica Neue, Helvetica, Arial, sans-serif" '
        f'fill="#6B665D">{escape(text)}</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


PLACEHOLDER = placeholder()


def fetch(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "hello-reporting"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


OG_IMAGE = re.compile(r'og:image"?\s+content="([^"]+)"')


def creative_from_permalink(
    permalink: str, fetcher: Callable[[str], bytes] = fetch
) -> tuple[str | None, str]:
    """A poszt nyitóképe a permalink `og:image` metaadatából.

    Akkor kell, ha a ZoomSphere nem tud a posztról — mert közvetlenül a
    felületen ment ki —, de a Meta Tartalom exportja igen. Ilyenkor a
    teljesítménye megvan, a kreatívja nincs, és a riportban helyőrző állna.

    Kimérve: a Facebook a `hello-reporting` néven is kiadja az `og:` mezőket;
    **nem kell a saját crawlerének kiadnunk magunkat**. Böngésző-User-Agenttel
    viszont 400-at ad, tehát ezek a mezők kifejezetten gépi olvasásra szólnak.

    **Az Instagram ugyanígy viselkedik.** Ezt a kód korábban tagadta — az állt
    itt, hogy „Instagramnál nincs og:image" —, és emiatt a FUP júliusi
    riportjában két IG-poszt helyén helyőrző maradt, pedig a permalinkjük élt.
    A tévedés akkor derült ki, amikor valaki tényleg lekérte: az Instagram 200-at
    ad, szabványos `og:image`-dzsel, `scontent.cdninstagram.com` hosztról. Amit
    nem mérünk ki, azt ne állítsuk.

    Két feltétele van, és mindkettő kicsúszhat alólunk: az oldal legyen
    nyilvános, és a Facebook adja továbbra is ezt a metaadatot. Ezért ez
    **kiegészítés, nem forrás** — ha nem megy, marad a helyőrző, és a
    `--validate` akkor is felsorolja a posztot.

    `(url, indoklás)` párt ad vissza. Az indoklás azért kell, mert a
    Mammut-próbán mindhárom pótlási kísérlet eredménytelen maradt, és nem
    derült ki, miért — így a menedzser nem tudta eldönteni, érdemes-e kézzel
    pótolni a képet.
    """
    if not permalink:
        return None, "nincs permalink a poszthoz"
    if not any(host in permalink for host in ("facebook.com", "instagram.com")):
        return None, "nem Facebook- vagy Instagram-link"
    try:
        page = fetcher(permalink).decode("utf-8", errors="replace")
    except Exception as error:
        return None, f"az oldal nem érhető el ({type(error).__name__})"
    if not page.strip():
        return None, "üres válasz (offline mód?)"
    found = OG_IMAGE.search(page)
    if not found:
        return None, "nincs og:image a lapon (nem nyilvános oldal?)"
    return unescape(found.group(1)), "megvan"


def parallel(function: Callable, items: list) -> list:
    """`function` minden elemre, párhuzamosan, a sorrendet megtartva."""
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(items))) as pool:
        return list(pool.map(function, items))


def to_data_uri(raw: bytes, max_width: int = MAX_WIDTH) -> str:
    image = Image.open(io.BytesIO(raw))
    # A telefonos fotók elforgatását az EXIF mondja meg, és a JPEG-újrakódolás
    # ezt eldobná: a kép oldalra fordulva jelent volna meg.
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        image = Image.new("RGB", rgba.size, PAPER)
        image.paste(rgba, mask=rgba.getchannel("A"))
    else:
        image = image.convert("RGB")
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
    """Minden URL-ből data URI. Ami nem tölthető le, helyőrzőt kap.

    Minden URL-t egyszer, párhuzamosan töltünk le. A gyorsítótár kulcsa
    szándékosan csak az URL: a Facebook CDN-linkjei lejárnak, és egy régi
    riport újrarenderelésekor a képnek sokszor a gyorsítótár az egyetlen
    példánya.
    """
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    def one(url: str) -> str:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        cached = cache / f"{key}.txt"
        if cached.exists():
            return cached.read_text(encoding="ascii")
        try:
            uri = to_data_uri(fetcher(url), max_width=max_width)
        except Exception:
            return PLACEHOLDER
        # Előbb ideiglenes fájlba, aztán átnevezés: egy megszakított futás ne
        # hagyjon félig írt, olvashatatlan képet a gyorsítótárban.
        partial = cached.with_suffix(".part")
        partial.write_text(uri, encoding="ascii")
        partial.replace(cached)
        return uri

    unique = list(dict.fromkeys(urls))
    resolved = dict(zip(unique, parallel(one, unique)))
    return [resolved[url] for url in urls]
