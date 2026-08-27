import pytest

from pipeline.build import load_narrative
from pipeline.errors import NarrativeError
from pipeline.narrative import BLOCKS, OPTIONAL_BLOCKS, resolve, resolve_all


def test_a_broken_narrative_json_names_the_likely_cause(tmp_path):
    """A narratívát kézzel is szerkesztik, és a magyar idézőjel könnyen
    egyenessel záródik — az pedig lezárja a JSON-stringet. Ez élesben meg is
    történt, és nyers stack trace jött rá."""
    (tmp_path / "narrative.json").write_text(
        '{"executive_summary": "a „Mert közösen a legjobb" bejegyzés"}',
        encoding="utf-8",
    )

    with pytest.raises(NarrativeError) as caught:
        load_narrative(tmp_path)

    message = str(caught.value)
    assert "nem érvényes JSON" in message
    assert "sor" in message, "mondjuk meg, hol"
    assert "idézőjel" in message, "mondjuk meg a valószínű okot"

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

    assert OPTIONAL_BLOCKS["campaign_status"]["label"]
    assert OPTIONAL_BLOCKS["campaign_status"]["guidance"]


def test_the_shipped_narrative_passes_the_number_check():
    """A fixture narratívája ugyanazon a szűrőn megy át, mint bármelyik másik.

    Ez az egyetlen valódi, kézzel írt narratíva a repóban — ha a mezőnevek
    elmozdulnak, itt derül ki elsőként.
    """
    import json
    from pathlib import Path

    base = Path(__file__).parent / "fixtures" / "larus-2026-07"
    data = json.loads((base / "report_data.golden.json").read_text(encoding="utf-8"))
    narrative = json.loads((base / "narrative.json").read_text(encoding="utf-8"))

    resolved = resolve_all(narrative, data)

    from pipeline.narrative import REFERENCE

    assert set(resolved) == set(BLOCKS), "minden blokknak meg kell lennie"
    assert not REFERENCE.search(json.dumps(resolved)), "maradt feloldatlan hivatkozás"
    assert resolved["key_finding"]["title"]
    assert len(resolved["next_steps"]) >= 3


def test_line_breaks_survive_into_the_rendered_html():
    """A szerkesztő Enterét a riportnak meg kell tartania.

    A `<p>`-be tett nyers sortörést a böngésző szóközzé olvasztja, tehát a
    mentés után a tördelés eltűnik — pedig a menedzser tényleg megnyomta az
    Entert. A sortörésből `<br>` kell legyen.
    """
    from pipeline.narrative import resolve_markup

    out = resolve_markup("Első bekezdés.\nMásodik bekezdés.", {})
    assert "<br>" in out
    assert "Első bekezdés." in out and "Második bekezdés." in out


def test_escaping_still_applies_around_the_line_break():
    """A sortörés nem nyithat kaput a nyers HTML-nek."""
    from pipeline.narrative import resolve_markup

    out = resolve_markup("a <b>x</b>\n<script>", {})
    assert "<b>" not in out and "<script>" not in out
    assert "&lt;b&gt;" in out and "<br>" in out
