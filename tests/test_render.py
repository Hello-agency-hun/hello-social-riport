import json
import re
from pathlib import Path

import pytest

from pipeline.render import render

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)


@pytest.fixture
def data():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture
def html(data, tmp_path):
    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def test_report_is_a_single_self_contained_file(html):
    """Se külső kép, se külső font, se külső script."""
    assert "<html" in html and "</html>" in html
    assert not re.search(r'(src|href)="https?://', html)


def test_every_section_is_a_16_by_9_page(html):
    assert html.count('class="page') >= 8


def test_cover_shows_client_and_period(html):
    assert "Larus Étterem" in html
    assert "2026" in html


def test_decimals_use_a_hungarian_comma(html):
    """Magyar riportban `33,2×`, nem `33.2×`.

    A `33.2` önmagában nem kereshető: a logó SVG-jének koordinátái között is
    előfordul. A tizedesjel a megjelenített értéknél számít.
    """
    assert "33,2×" in html
    assert "33.2×" not in html


def test_key_numbers_appear(html):
    assert "4 312" in html
    assert "130" in html
    assert "472" in html


def test_stylesheet_is_not_html_escaped(html):
    """Escape-elve az idézőjelek `&#34;`-re válnak, és a `@font-face` elromlik.

    A tünet néma: a layout és a színek jók maradnak, csak a riport talpas
    fallback fontra vált — pont az, amit egy teszt nélkül senki nem vesz észre.
    """
    start = html.index("<style>")
    css = html[start : html.index("</style>", start)]
    assert "&#34;" not in css and "&quot;" not in css
    assert '@font-face' in css
    assert 'src: url("data:font/woff2;base64,' in css
    assert '--font: "Open Sauce One"' in css


def test_client_supplied_text_is_still_escaped(data, tmp_path):
    """A stíluslap `| safe`, de a poszt-szövegek nem lehetnek azok."""
    top = max(data["posts"], key=lambda post: post["reach"])
    top["caption"] = "<script>alert(1)</script>"
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_logo_is_embedded_as_vector(html):
    assert html.count("<svg") >= 3, "címlap-lockup, záró-mark és a grafikonok"
    assert 'fill="currentColor"' in html


def test_narrative_sections_are_omitted_without_narrative(html):
    """A 3. terv előtt nincs narratíva — helykitöltő szöveg sem lehet."""
    assert "Lorem" not in html
    assert "TODO" not in html


def test_numbers_use_hungarian_thousand_separator(html):
    assert "18 811" in html


def test_render_is_deterministic(data, tmp_path):
    first = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    second = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    assert first == second


def test_machine_identifiers_never_reach_the_client(html):
    """A Meta belső kulcsai nem kerülhetnek ki az ügyfélnek szánt riportba."""
    for raw in (
        "actions:omni_landing_page_view",
        "actions:post_engagement",
        "profile_visit_view",
        "link_clicks",
        "LINK_CLICKS",
    ):
        assert raw not in html, f"nyers azonosító a riportban: {raw}"


def test_labels_are_hungarian(html):
    assert "Érkezésioldal-megtekintés" in html
    assert "Hivatkozáskattintások" in html
    assert "Facebook" in html and "Instagram" in html


def test_unknown_identifier_falls_back_to_the_raw_value():
    """Új Meta-eredménytípus látszódjon csúnyán, de ne tűnjön el."""
    from pipeline.labels import result_type

    assert result_type("actions:teljesen_uj") == "actions:teljesen_uj"


def test_each_channel_gets_daily_trend_charts(html):
    assert html.count('class="chart"') >= 8, "csatornánként 4 metrika trendgörbéje"


def test_trend_chart_labels_are_hungarian(html):
    assert "Felkeresések" in html
    assert "Interakciók" in html
