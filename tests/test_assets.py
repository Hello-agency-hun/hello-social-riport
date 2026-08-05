from pathlib import Path

import pytest

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
WEIGHTS = ["Regular", "Medium", "Bold", "Black"]


@pytest.mark.parametrize("weight", WEIGHTS)
def test_font_is_vendored(weight):
    path = FONTS / f"OpenSauceOne-{weight}.woff2"
    assert path.exists(), f"{path.name} hiányzik — futtasd: python tools/vendor_fonts.py"
    assert path.read_bytes()[:4] == b"wOF2", "nem woff2 fájl"


def test_licence_is_shipped():
    """OFL: a licencszöveget együtt kell terjeszteni a fonttal."""
    assert (FONTS / "OFL.txt").exists()


LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo"


@pytest.mark.parametrize("name", ["hello-mark", "hello-lockup"])
def test_logo_is_vector_and_inherits_colour(name):
    """A brand guide tiltja a logó átszínezését; a `currentColor` miatt az
    egyetlen szín, amit felvehet, a szövegszín (--ink) — nem lehet elrontani."""
    svg = (LOGO / f"{name}.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg")
    assert 'fill="currentColor"' in svg
    assert "viewBox" in svg
    assert "<image" not in svg, "raszterkép nem kerülhet a logóba"
