import pytest

from pipeline.errors import NarrativeError
from pipeline.narrative import BLOCKS, resolve, resolve_all

DATA = {
    "meta": {"client": "Larus Étterem", "period": "2026-07"},
    "paid": {"spend": 472.71, "currency": "EUR"},
    "cross": {
        "avg_reach_organic_post": 130,
        "avg_reach_boosted_post": 4312,
        "reach_multiplier": 33.2,
        "boosted_share_of_post_reach": 0.917,
        "boost_spend": 57.62,
    },
}


def test_plain_reference_is_formatted_hungarian():
    """Ezres elválasztó nem törhető szóköz — a szám nem törhet két sorba."""
    assert resolve("{cross.avg_reach_boosted_post} ember", DATA) == (
        "4 312 ember"
    )


def test_money_formatter():
    assert resolve("{paid.spend|money}", DATA) == "472,71 EUR"


def test_percentage_formatter():
    assert resolve("{cross.boosted_share_of_post_reach|pct}", DATA) == "91,7%"


def test_multiplier_formatter():
    assert resolve("{cross.reach_multiplier|x}", DATA) == "33,2×"


def test_month_formatter():
    assert resolve("{meta.period|month}", DATA) == "2026. július"


def test_raw_formatter_passes_strings_through():
    assert resolve("{meta.client|raw}", DATA) == "Larus Étterem"


def test_a_written_number_is_refused():
    """Ez a projekt legfontosabb szabálya: számot nem lehet leírni, csak hivatkozni."""
    with pytest.raises(NarrativeError, match="leírt szám"):
        resolve("A boost 33,2-szeresére növelte az elérést.", DATA)


def test_a_written_number_is_refused_even_next_to_a_reference():
    with pytest.raises(NarrativeError, match="leírt szám"):
        resolve("{cross.avg_reach_organic_post} helyett 4312 ember.", DATA)


def test_unknown_field_stops_the_build():
    with pytest.raises(NarrativeError, match="nincs ilyen mező"):
        resolve("{cross.nincs_ilyen}", DATA)


def test_unknown_formatter_stops_the_build():
    with pytest.raises(NarrativeError, match="ismeretlen formázó"):
        resolve("{paid.spend|forint}", DATA)


def test_resolve_all_walks_the_whole_structure():
    narrative = {
        "executive_summary": "{cross.reach_multiplier|x} a különbség.",
        "what_worked": ["{paid.spend|money} költés."],
        "key_finding": {"title": "Címsor", "body": "{cross.avg_reach_organic_post}"},
    }
    out = resolve_all(narrative, DATA)
    assert out["executive_summary"] == "33,2× a különbség."
    assert out["what_worked"] == ["472,71 EUR költés."]
    assert out["key_finding"]["body"] == "130"


def test_every_declared_block_is_documented():
    """A séma írja le önmagát — a SKILL.md ebből dolgozik."""
    for key, meta in BLOCKS.items():
        assert meta["label"], key
        assert meta["guidance"], f"{key}: nincs megadva, mit írjon bele"
