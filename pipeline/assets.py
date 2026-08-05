"""A stíluslap, a fontok és a logó beágyazása."""

import base64
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


@lru_cache(maxsize=1)
def stylesheet() -> str:
    """brand.css + print.css, a fontokkal beágyazva."""
    css = (TEMPLATES / "brand.css").read_text(encoding="utf-8")
    for slot, filename in FONT_SLOTS.items():
        css = css.replace(slot, _data_uri(FONTS / filename))
    css += "\n" + (TEMPLATES / "print.css").read_text(encoding="utf-8")
    return css
