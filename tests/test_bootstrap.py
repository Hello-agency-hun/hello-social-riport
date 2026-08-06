import pytest

from pipeline.bootstrap import suggest, template
from pipeline.errors import UnknownSourceError
from pipeline.parsers import meta_daily


def test_suggest_reads_the_identifiers_out_of_the_content_export(fixture_dir):
    found = suggest(fixture_dir / "input")
    assert found["fb_page_id"] == "100064824963030"
    assert found["fb_page_name"] == "Larus Étterem"
    assert found["name"] == "Larus Étterem"


def test_suggest_reads_the_currency_out_of_the_ads_export(fixture_dir):
    assert suggest(fixture_dir / "input")["currency"] == "EUR"


def test_suggest_never_raises_on_a_folder_it_cannot_read(tmp_path):
    """A bootstrap akkor fut, amikor a menedzser már hibahelyzetben van.
    Ha ő maga elszáll, elveszi az egyetlen segítséget is."""
    (tmp_path / "kacat.csv").write_text("nem, ez, semmi\n1,2,3\n", encoding="utf-8")
    (tmp_path / "ures.csv").write_text("", encoding="utf-8")
    assert suggest(tmp_path) == {}
    assert suggest(tmp_path / "nincs-ilyen") == {}


def test_template_keeps_placeholders_for_what_we_could_not_find():
    text = template({"fb_page_id": "123"})
    assert 'fb_page_id: "123"' in text
    assert "<a Facebook-oldal pontos neve>" in text


def test_an_ambiguous_daily_tile_gets_a_pasteable_answer(fixture_dir, tmp_path):
    """A `Megtekintések` csempe az egyetlen, ami nem árulja el a csatornáját.
    A hibaüzenet eddig annyit mondott: „add hozzá a overrides szakaszhoz" —
    de sem a formátumot, sem a választható mezőneveket nem mutatta meg."""
    source = fixture_dir / "input" / "Megtekintések-2.csv"

    with pytest.raises(UnknownSourceError) as caught:
        meta_daily.parse(source)

    message = str(caught.value)
    assert "daily_metric_overrides:" in message, "a kimásolható szakasz"
    # A mezőnév kiolvasható a csempe magyar nevéből — azt nem kell találgatni.
    assert '"Megtekintések": [' in message and '"views"' in message
    # A csatornát viszont ez a csempe tényleg nem árulja el. Nem tippelünk
    # helyette: mindkét lehetőség ott van, a döntés a menedzseré.
    assert "facebook" in message and "instagram" in message
    # a választható mezőnevek, hogy ne kelljen a kódban keresgélni
    assert "link_clicks" in message
