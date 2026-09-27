"""A stíluslap, a fontok és a logó beágyazása."""

import base64
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
TEMPLATES = ROOT / "templates"

FONT_SLOTS = {
    "__FONT_REGULAR__": "OpenSauceOne-Regular.woff2",
    "__FONT_MEDIUM__": "OpenSauceOne-Medium.woff2",
    "__FONT_BOLD__": "OpenSauceOne-Bold.woff2",
    "__FONT_BLACK__": "OpenSauceOne-Black.woff2",
}


def _data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:font/woff2;base64,{encoded}"


@lru_cache(maxsize=8)
def logo(name: str) -> str:
    """A logó SVG-je, beágyazásra. `currentColor`-t használ, tehát a
    szövegszínt veszi fel — a brand guide tiltja az önálló átszínezést."""
    return (ROOT / "assets" / "logo" / f"{name}.svg").read_text(encoding="utf-8")


# A stíluslap és a szerkesztő-script kommentjei a fejlesztőknek szólnak.
# Beágyazva minden kiküldött riport forrásában ott utaznának — belső
# jegyzetként, ügyfélről ügyfélre, fölösleges kilobájtokként.
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _without_css_comments(css: str) -> str:
    # A base64 ábécében nincs `*`, így egy font data URI-ban sem fordulhat
    # elő `/*` — a kommentek a fontok beillesztése előtt is, után is
    # biztonsággal kivághatók. Mi előtte vágjuk, olcsóbb.
    return re.sub(r"\n{3,}", "\n\n", CSS_COMMENT.sub("", css))


def without_js_line_comments(source: str) -> str:
    """A csak kommentből álló sorok nélkül. A sor végi kommentekhez nem
    nyúlunk: JavaScriptet nem elemzünk, és egy `//` állhat stringben vagy
    reguláris kifejezésben is."""
    return "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("//")
    )


@lru_cache(maxsize=1)
def stylesheet() -> str:
    """brand.css + print.css, a fontokkal beágyazva, kommentek nélkül."""
    css = _without_css_comments((TEMPLATES / "brand.css").read_text(encoding="utf-8"))
    for slot, filename in FONT_SLOTS.items():
        css = css.replace(slot, _data_uri(FONTS / filename))
    css += "\n" + _without_css_comments((TEMPLATES / "print.css").read_text(encoding="utf-8"))
    return css


@lru_cache(maxsize=1)
def review_script() -> str:
    """A böngészőoldali szerkesztő, a kommentsorok nélkül."""
    return without_js_line_comments((TEMPLATES / "review.js").read_text(encoding="utf-8"))
