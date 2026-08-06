import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parent.parent / "templates" / "brand.css"

# A benchmark riportból mért paletta. Ha ez elmozdul, a riport eltér a HELLO
# vizuális rendszerétől — ezért van tesztbe kötve, nem csak dokumentálva.
TOKENS = {
    "--ink": "#0A0A0A",
    "--ink-soft": "#6B665D",
    "--rule": "#E4E0D8",
    "--paper": "#FFFDF9",
    "--paper-alt": "#FAFAFA",
    "--accent": "#4CD892",
    "--brand-rose": "#FF33CC",
    "--brand-sun": "#FFFA8E",
    "--brand-pink": "#FF91E7",
    "--brand-red": "#FF321D",
    "--brand-blue": "#025CC6",
}


@pytest.mark.parametrize("token, value", TOKENS.items())
def test_token_has_the_measured_value(token, value):
    text = CSS.read_text(encoding="utf-8")
    match = re.search(rf"{re.escape(token)}\s*:\s*(#[0-9A-Fa-f]{{6}})", text)
    assert match, f"{token} nincs definiálva a brand.css-ben"
    assert match.group(1).upper() == value


def test_page_is_16_by_9():
    text = CSS.read_text(encoding="utf-8")
    assert "--page-w: 1440px" in text
    assert "--page-h: 810px" in text


def test_fonts_are_embedded_by_placeholder_not_by_url():
    """A kész HTML offline is működik — külső fonthivatkozás nem maradhat benne."""
    text = CSS.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in text
    assert "http://" not in text and "https://" not in text


def test_creatives_are_shown_whole_not_cropped():
    """Álló poszt-képnél a `cover` levágná a kreatív felét."""
    text = CSS.read_text(encoding="utf-8")
    thumb = text[text.index(".thumb") : text.index(".thumb") + 400]
    assert "object-fit: contain" in thumb
    assert "cover" not in thumb


def test_list_items_carry_their_own_size():
    """A `p, li, td, th` szabály felülírja az öröklést, ezért a listaelem
    méretét magán az `li`-n kell megadni, nem a szülő `ol`-on."""
    template = (
        Path(__file__).resolve().parent.parent
        / "templates"
        / "sections"
        / "narrative.html.j2"
    ).read_text(encoding="utf-8")
    for line in template.splitlines():
        if "<li" in line:
            assert "font-size" in line, f"méret nélküli listaelem: {line.strip()[:60]}"


def test_stat_tiles_share_a_baseline():
    """A pénznem-csempe kisebb betűs; enélkül a felirata följebb csúszna."""
    text = CSS.read_text(encoding="utf-8")
    stat = text[text.index(".stat {") : text.index(".stat--sm")]
    assert "min-height" in stat
    assert "align-items: flex-end" in stat


DESIGN_PAGE = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "hello-report"
    / "references"
    / "design-system.html"
)


def test_the_design_system_page_matches_the_stylesheet():
    """A dokumentum generált — ha elcsúszna a brand.css-től, semmit nem érne."""
    assert DESIGN_PAGE.exists(), "futtasd: python tools/build_styleguide.py"
    html = DESIGN_PAGE.read_text(encoding="utf-8")
    for token, value in TOKENS.items():
        assert f"<code>{token}</code><b>{value}</b>" in html, token


def test_the_design_system_page_stays_small_enough_to_read():
    """A plugin a kontextusába olvassa be — a beágyazott fontok itt pazarlás."""
    html = DESIGN_PAGE.read_text(encoding="utf-8")
    assert "data:font/woff2" not in html
    assert DESIGN_PAGE.stat().st_size < 60_000, DESIGN_PAGE.stat().st_size


def test_the_design_system_page_carries_copyable_markup():
    """Az érték a másolható mintában van, nem a rendereltségben."""
    html = DESIGN_PAGE.read_text(encoding="utf-8")
    for snippet in ("class=&quot;stat", "class=&quot;manual-slot", "data-narrative"):
        assert snippet in html, snippet
