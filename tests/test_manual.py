import json
from pathlib import Path

import pytest

from pipeline.manual import OBTAINABLE, SLOTS, load_manual

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)
NBSP = " "


def test_missing_file_yields_an_empty_mapping(tmp_path):
    assert load_manual(tmp_path) == {}


def test_values_are_read_from_review_json(tmp_path):
    (tmp_path / "review.json").write_text(
        json.dumps({"manual": {"prev_facebook_visits": 1113}}), encoding="utf-8"
    )
    assert load_manual(tmp_path)["prev_facebook_visits"] == 1113


def test_every_slot_says_where_to_get_it():
    """A mező önmagában semmit nem ér — meg kell mondania, honnan szerezhető be."""
    for key, slot in SLOTS.items():
        assert slot["label"], key
        assert slot["hint"], f"{key}: nincs megadva, honnan szerezhető be"


def test_everything_obtainable_says_where_and_why():
    """A `--validate` ebből dolgozik. Nem elég tudni, hogy hiányzik — azt is meg
    kell mondani, hol van, és miért nem tudjuk kiszámolni helyette."""
    for key, spec in OBTAINABLE.items():
        assert spec["why"], f"{key}: nincs megadva, miért nem számolható"
        for channel, hint in spec["hint"].items():
            assert hint, f"{key}/{channel}: nincs megadva, hol van"


def test_the_reach_tile_is_named_per_channel():
    """A Facebookon nincs „Elérés” csempe — ott „Nézők” a neve ugyanannak.
    Egyetlen közös útmutató a rossz csempéhez küldi a menedzsert, és a
    „Megtekintések”-et hozza el, ami megjelenést mér, nem embert."""
    hint = OBTAINABLE["monthly_reach"]["hint"]

    assert "Nézők" in hint["facebook"]
    assert "Megtekintések" in hint["facebook"], "a tévedést nevezzük is meg"
    assert "Elérés" in hint["instagram"]


@pytest.fixture
def data():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture
def empty(data, tmp_path):
    from pipeline.render import render

    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def test_no_empty_dashed_box_reaches_the_client(empty):
    """Üres, szaggatott dobozok álltak a riportban olyan adatokra, amiket a Meta
    nem exportál. Az ügyfél ebből azt olvasta ki, hogy elfelejtettünk valamit.
    Ami mérve van, azt mutatjuk; a többiről a `--validate` szól."""
    assert 'data-manual="reach_facebook"' not in empty
    assert 'data-manual="reach_instagram"' not in empty
    # Az összehasonlító oldal előző havi mezői maradnak: azok nem beszerzési
    # útmutatót mutatnak, hanem egy értéket, amit a menedzser már ismer.
    assert "Elérés csempe" not in empty, "a beszerzési útmutató a menedzsernek szól"


def test_the_slot_mechanism_still_hides_itself_when_printing(empty):
    """A mechanizmus megmarad — az összehasonlító oldal előző havi mezői
    használják —, csak a fókusz-oldalról került le."""
    css = empty[empty.index("<style>") : empty.index("</style>")]
    printed = css[css.index("@media print") :]
    assert ".manual-slot" in printed and "display: none" in printed


def test_monthly_reach_appears_when_it_was_supplied(data, tmp_path):
    """Ha a menedzser leolvasta, ez a legerősebb szám a lapon: az egyetlen
    deduplikált érték, amit a Meta ad."""
    from pipeline.render import render

    data["audience"]["facebook"]["monthly_reach"] = 92400
    data["audience"]["facebook"]["reach_per_follower"] = 22.1
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"").replace(NBSP, " ")

    assert "92 400" in html
    assert "havi elérés" in html
    assert "22,1× a követőtábor" in html
