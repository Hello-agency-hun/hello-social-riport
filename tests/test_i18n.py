"""A riport nyelve.

Az angol próbafutáson három szivárgás derült ki, és egyiket sem a kód
olvasásából találtam meg: a JavaScriptből injektált gombfeliratok, a diagram
lábában az „összesen", és a diagramok magyar számformátuma. Mindhárom olyan,
ami csak a megrenderelt riporton látszik — ezért ezek a tesztek a KÉSZ HTML-t
nézik, nem a forrást.
"""

import json
import re
from pathlib import Path

import pytest

from pipeline import charts, i18n
from pipeline.render import _money, _number, _period_name, render

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)
HUNGARIAN = re.compile(r"[őűáéíóöúüŐŰÁÉÍÓÖÚÜ]")


def test_every_language_has_every_key():
    """Hiányzó kulcsnál a `Strings` megáll — de jobb, ha ki sem kerül a repóba.
    Egy elfelejtett kulcs a riportban üres helyet hagyna."""
    reference = set(i18n.STRINGS["hu"])
    for language, table in i18n.STRINGS.items():
        missing = reference - set(table)
        extra = set(table) - reference
        assert not missing, f"{language}: hiányzik {sorted(missing)}"
        assert not extra, f"{language}: fölösleges {sorted(extra)}"


def test_a_typo_in_a_key_stops_rather_than_renders_empty():
    strings = i18n.strings("hu")
    with pytest.raises(AttributeError, match="nincs ilyen riportszöveg"):
        strings.nincs_ilyen_kulcs


def test_english_strings_are_not_hungarian():
    """Egy lefordítatlanul maradt érték csendben magyarul kerülne az angol
    riportba."""
    for key, value in i18n.STRINGS["en"].items():
        assert not HUNGARIAN.search(value), f"`{key}` magyarul maradt: {value!r}"


@pytest.mark.parametrize(
    "language,expected",
    [("hu", "26 836"), ("en", "26,836")],
    ids=["magyar-szokoz", "angol-vesszo"],
)
def test_thousands_follow_the_language(language, expected):
    assert _number(26836, 0, language).replace("\xa0", " ") == expected
    # A diagramok külön kódúton mennek — az angol próbán pont ezek maradtak ki.
    assert charts._thousands(26836, language).replace("\xa0", " ") == expected


def test_decimals_follow_the_language():
    assert _money(438.75, "EUR", "hu").replace("\xa0", " ") == "438,75 EUR"
    assert _money(438.75, "EUR", "en") == "438.75 EUR"
    assert _money(1200, "USD", "en") == "$1,200.00"


def test_month_names_follow_the_language():
    assert _period_name("2026-07", "hu") == "2026. július"
    assert _period_name("2026-07", "en") == "July 2026"


@pytest.fixture
def english_html(tmp_path):
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    data["meta"]["language"] = "en"
    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def _visible(html: str) -> str:
    body = html[html.index("<body>") :]
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S)
    body = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
    body = re.sub(r"data:image/[^\"']+", " ", body)
    return re.sub(r"<[^>]+>", " ", body)


def test_no_template_label_stays_hungarian(english_html):
    """A sablon minden felirata angol. A poszt-szövegek nem: azok az ügyfél
    saját tartalmai, és úgy idézzük őket, ahogy megjelentek."""
    for pattern in (
        r'<div class="eyebrow"[^>]*>(.*?)</div>',
        r'<div class="stat-label"[^>]*>(.*?)</div>',
        r"<th[^>]*>(.*?)</th>",
        r"<h3[^>]*>(.*?)</h3>",
    ):
        for found in re.findall(pattern, english_html, re.S):
            plain = re.sub(r"<[^>]+>", "", found).strip()
            assert not HUNGARIAN.search(plain), f"magyarul maradt: {plain!r}"


def test_the_javascript_button_labels_are_translated(english_html):
    """Ezek a sablonon kívül élnek, és az angol próbán magyarul maradtak egy
    egyébként teljesen angol riporton."""
    labels = re.search(r"window\.__helloLabels = (\{.*?\});", english_html, re.S)
    assert labels, "a feliratok nem kerültek be a lapra"

    injected = json.loads(labels.group(1))
    assert injected["save"] == "Save"
    assert injected["save_to_folder"] == "Save to folder"
    assert injected["comment"] == "comment"


def test_the_chart_footer_is_translated(english_html):
    assert "total " in english_html
    assert "összesen" not in english_html


def test_the_closing_page_thanks_the_reader(english_html):
    assert "Thank you for your interest" in english_html


def test_the_hungarian_report_stays_hungarian(tmp_path):
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")

    assert "A hónap számokban" in html
    assert "összesen" in html, "a diagram lába magyarul"
    assert "Köszönjük a kíváncsiságot" in html
