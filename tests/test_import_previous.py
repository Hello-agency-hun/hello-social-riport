from pathlib import Path

import pytest

from tools.import_previous import (
    harvest,
    pair_numbers_with_labels,
    parse_compact_number,
)

@pytest.fixture
def deck(tmp_path):
    """Egy Canva-szerű riportoldal, a valódi elrendezést utánozva.

    Korábban egy valódi ügyfél riportja állt a repó gyökerében, és ez a teszt
    azt olvasta. Két baj volt vele: ügyféladat került a nyilvános repóba, és a
    fájl pontosan úgy nézett ki, mint egy adatforrás — egy agent, akit
    megkérnek, hogy „csinálj riportot a Mammutnak", rátalálhatott.
    """
    pymupdf = pytest.importorskip("pymupdf")

    path = tmp_path / "deck.pdf"
    document = pymupdf.open()
    page = document.new_page(width=1200, height=700)
    page.insert_text((100, 200), "Instagram", fontsize=20)
    for x, number, label in (
        (108, "149.3K", "Impressions"),
        (549, "81.6K", "Reach"),
        (976, "852", "Interactions"),
    ):
        page.insert_text((x, 275), number, fontsize=28)
        page.insert_text((x + 7, 362), label, fontsize=12)

    page = document.new_page(width=1200, height=700)
    page.insert_text((100, 200), "Facebook", fontsize=20)
    for x, number, label in (
        (108, "170.6K", "Impressions"),
        (549, "92.4K", "Reach"),
        (976, "+34", "Followers"),
    ):
        page.insert_text((x, 275), number, fontsize=28)
        page.insert_text((x + 7, 362), label, fontsize=12)

    document.save(path)
    return path


@pytest.mark.parametrize(
    "text, expected",
    [
        ("149.3K", 149300),
        ("81.6K", 81600),
        ("4.9K", 4900),
        ("34.6K", 34600),
        ("852", 852),
        ("+200", 200),
        ("1 227", 1227),
        ("3.1K", 3100),
    ],
)
def test_compact_numbers_are_expanded(text, expected):
    assert parse_compact_number(text) == expected


@pytest.mark.parametrize("text", ["kb. sok", "", "Reach", "12K3"])
def test_unparseable_text_returns_none(text):
    assert parse_compact_number(text) is None


def test_label_below_the_number_wins_not_the_reading_order():
    """A szövegkinyerés a számokat és a feliratokat külön csoportban adja vissza.

    Sorrend alapján párosítva minden metrika ugyanazt az értéket kapná — ezért
    kell a geometria.
    """
    spans = [
        (108, 275, "149.3K"),
        (549, 275, "81.6K"),
        (976, 269, "852"),
        (115, 362, "Impressions"),
        (549, 362, "Reach"),
        (982, 357, "Interactions"),
    ]
    assert pair_numbers_with_labels(spans) == {
        "impressions": 149300,
        "reach": 81600,
        "interactions": 852,
    }


def test_a_plus_sign_marks_a_change_not_a_total():
    """`+200 Followers` a havi növekmény, nem a követő-összlétszám."""
    spans = [(534, 537, "+200"), (540, 625, "Followers")]
    assert pair_numbers_with_labels(spans) == {"followers_change": 200}


def test_a_number_without_a_label_below_is_ignored():
    assert pair_numbers_with_labels([(100, 500, "999")]) == {}


def test_hungarian_labels_are_recognised():
    spans = [(100, 100, "957"), (100, 180, "Felkeresések")]
    assert pair_numbers_with_labels(spans) == {"visits": 957}


def test_a_whole_deck_is_read_channel_by_channel(deck):
    """Végponttól végpontig: PDF-ből metrikák, csatornánként szétválasztva.

    A csatornát az oldal fejléce dönti el, nem a sorrend — egy deckben
    tetszőleges számú oldal lehet, és a metrikanevek ismétlődnek."""
    import pymupdf

    found = harvest(pymupdf.open(deck))

    assert found["instagram"]["impressions"] == 149300
    assert found["instagram"]["reach"] == 81600
    assert found["instagram"]["interactions"] == 852
    assert found["facebook"]["reach"] == 92400
    assert found["facebook"]["impressions"] == 170600
    # `+34 Followers` a havi növekmény, nem a követő-összlétszám
    assert found["facebook"]["followers_change"] == 34
