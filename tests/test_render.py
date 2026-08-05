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
    facebook = data["channels"]["facebook"]["posts"]
    top = max(facebook, key=lambda post: post["reach"])
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


def _visible_text(html: str) -> str:
    """Csak az, amit az olvasó lát: tagek, attribútumok és a style/script nélkül.

    A gépi kulcsok legitim módon szerepelnek `data-manual` attribútumokban és a
    beágyazott JS-ben — a tilalom a látható szövegre vonatkozik.
    """
    body = re.sub(r"<(style|script).*?</>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", body)


def test_machine_identifiers_never_reach_the_client(html):
    """A Meta belső kulcsai nem kerülhetnek az ügyfél szeme elé."""
    visible = _visible_text(html)
    for raw in (
        "actions:omni_landing_page_view",
        "actions:post_engagement",
        "profile_visit_view",
        "link_clicks",
        "LINK_CLICKS",
    ):
        assert raw not in visible, f"nyers azonosító a riportban: {raw}"


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


def test_report_has_a_section_per_channel(html):
    assert ">Instagram<" in html
    assert ">Facebook<" in html


def test_six_posts_are_shown_for_the_measured_channel(html):
    """Facebookon 16 mért poszt van — hatot mutatunk, két oldalon."""
    assert html.count('class="thumb"') >= 6


def test_post_metrics_show_measured_numbers_not_a_subtraction(html):
    """Összes elérés és fizetett kampány-elérés — organikus becslés nélkül."""
    assert "ebből fizetett" in html
    assert "becsült" not in html.lower()


def test_page_count_stays_within_the_agreed_limit(html):
    assert 12 <= html.count('class="page') <= 20


def test_channel_kpi_tiles_use_hungarian_labels(html):
    assert "Hivatkozáskattintások" in html
    assert "Új követők" in html


def test_report_does_not_apologise_to_the_client(html):
    """A hiánylista a menedzsernek szól, nem az ügyfélnek."""
    for phrase in ("nem illesztett", "Nem becsültük meg", "nem közöl ilyen számot"):
        assert phrase not in html


def test_quality_block_still_records_everything(data):
    """A belső szigor nem lazul: a JSON-ban minden hiány rögzítve marad."""
    for key in ("unmatched_boosts", "unmatched_content", "dropped_zero_campaign_rows",
                "posts_measured"):
        assert key in data["quality"]


def test_summary_page_shows_the_six_key_numbers(html):
    assert "A hónap mérlege" in html
    assert "a boost szorzója" in html


def test_pages_are_balanced_so_no_card_is_left_alone():
    """Négy poszt 3+1 helyett 2+2 — árva kártya nem marad egy üres lapon."""
    from pipeline.render import _balanced_chunks

    assert [len(c) for c in _balanced_chunks([1, 2, 3, 4])] == [2, 2]
    assert [len(c) for c in _balanced_chunks([1, 2, 3, 4, 5])] == [3, 2]
    assert [len(c) for c in _balanced_chunks([1, 2, 3, 4, 5, 6])] == [3, 3]
    assert [len(c) for c in _balanced_chunks([1, 2, 3])] == [3]
    assert _balanced_chunks([]) == []


def test_paid_only_posts_do_not_say_ebbol(html):
    """`ebből fizetett` csak akkor értelmes, ha van mihez képest."""
    assert "fizetett elérés" in html


NARRATIVE = {
    "executive_summary": "A boost {cross.reach_multiplier|x}-ra emelte az elérést.",
    "key_finding": {
        "title": "A boost megtérül",
        "body": "Organikusan {cross.avg_reach_organic_post} ember, boosttal "
        "{cross.avg_reach_boosted_post}.",
    },
    "what_worked": ["A séf-ajánlat vitte a legtöbb elérést."],
    "what_to_improve": ["Az Instagram-tartalom mérése hiányos."],
    "next_steps": ["Töltsük le az Instagram Tartalom exportot."],
}


def test_narrative_pages_are_absent_without_narrative(html):
    assert "Vezetői összefoglaló" not in html


def test_narrative_pages_appear_when_given(data, tmp_path):
    out = render(data, cache_dir=tmp_path, fetcher=lambda url: b"", narrative=NARRATIVE)
    assert "Vezetői összefoglaló" in out
    assert "A boost megtérül" in out
    assert "33,2×-ra emelte" in out
    assert "Következő lépések" in out


def test_narrative_references_are_substituted_not_shown_raw(data, tmp_path):
    out = render(data, cache_dir=tmp_path, fetcher=lambda url: b"", narrative=NARRATIVE)
    assert "{cross." not in out


def test_narrative_with_a_written_number_stops_the_build(data, tmp_path):
    from pipeline.errors import NarrativeError

    with pytest.raises(NarrativeError):
        render(
            data,
            cache_dir=tmp_path,
            fetcher=lambda url: b"",
            narrative={"executive_summary": "A boost 33,2-szeresére emelte."},
        )
