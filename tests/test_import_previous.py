from pathlib import Path

import pytest

from tools.import_previous import (
    harvest,
    pair_numbers_with_labels,
    parse_compact_number,
)

MAMMUT = Path(__file__).resolve().parent.parent / "Mammut_july_social_riport_2026.pdf"


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


@pytest.mark.skipif(not MAMMUT.exists(), reason="a Mammut riport nincs a repóban")
def test_real_report_yields_the_printed_values():
    """A tényleges PDF-ből kiolvasott értékek — kézzel ellenőrizve a riporton."""
    import pymupdf

    found = harvest(pymupdf.open(MAMMUT))
    assert found["instagram"] == {
        "impressions": 149300,
        "interactions": 852,
        "reach": 81600,
        "visits": 957,
        "followers_change": 200,
        "link_clicks": 778,
    }
    assert found["facebook"]["reach"] == 92400
    assert found["facebook"]["impressions"] == 170600
    assert found["facebook"]["followers_change"] == 34
