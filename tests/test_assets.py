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


def test_stylesheet_inlines_the_fonts_as_data_uris():
    from pipeline.assets import stylesheet

    css = stylesheet()
    assert "__FONT_REGULAR__" not in css, "a helyőrzőket ki kell cserélni"
    assert css.count("data:font/woff2;base64,") == 4
    assert "@page" in css, "a print.css-nek is benne kell lennie"


def test_last_report_page_does_not_create_a_blank_pdf_page():
    """A riportoldalak utan script tagek jonnek, ezert a :last-child nem talalna
    el az utolso sectionre, es a kotelezo oldaltores egy ures PDF-lapot adna.
    """
    from pipeline.assets import stylesheet

    css = stylesheet()
    assert ".page:last-of-type" in css
    assert ".page:last-child" not in css


def test_stylesheet_has_no_external_reference():
    """A kész riport offline is működik."""
    from pipeline.assets import stylesheet

    css = stylesheet()
    assert "http://" not in css and "https://" not in css


def test_logo_loader_returns_inline_svg():
    from pipeline.assets import logo

    assert logo("hello-mark").startswith("<svg")
    assert 'fill="currentColor"' in logo("hello-lockup")
