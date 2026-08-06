import json

import pytest

from pipeline.errors import NarrativeError
from pipeline.narrative import resolve_all
from pipeline.review import apply_edits, load_review


def test_missing_file_yields_empty_sections(tmp_path):
    assert load_review(tmp_path) == {"manual": {}, "edits": {}, "comments": []}


def test_sections_are_read(tmp_path):
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "manual": {"reach_facebook": 92400},
                "edits": {"executive_summary": "Átírt szöveg."},
                "comments": [{"page": 12, "text": "ide kérek kördiagramot"}],
            }
        ),
        encoding="utf-8",
    )
    review = load_review(tmp_path)
    assert review["manual"]["reach_facebook"] == 92400
    assert review["edits"]["executive_summary"] == "Átírt szöveg."
    assert review["comments"][0]["page"] == 12


def test_a_partial_file_still_yields_every_section(tmp_path):
    (tmp_path / "review.json").write_text(
        json.dumps({"comments": [{"page": 1, "text": "x"}]}), encoding="utf-8"
    )
    review = load_review(tmp_path)
    assert review["manual"] == {}
    assert review["edits"] == {}


def test_edits_replace_narrative_blocks():
    narrative = {"executive_summary": "Eredeti.", "what_worked": ["a"]}
    edited = apply_edits(narrative, {"executive_summary": "Átírt."})
    assert edited["executive_summary"] == "Átírt."
    assert edited["what_worked"] == ["a"]


def test_edits_cannot_invent_a_new_block():
    """A review.json nem hozhat létre új narratíva-blokkot."""
    edited = apply_edits({"executive_summary": "a"}, {"kitalalt_blokk": "b"})
    assert "kitalalt_blokk" not in edited


def test_edited_text_still_goes_through_the_number_check():
    """A kézzel átírt szöveg sem tartalmazhat leírt számot — ez nem kiskapu."""
    edited = apply_edits(
        {"executive_summary": "{cross.reach_multiplier|x}"},
        {"executive_summary": "A boost 33,2-szeres."},
    )
    with pytest.raises(NarrativeError):
        resolve_all(edited, {"cross": {"reach_multiplier": 33.2}})


def test_manual_values_now_come_from_review_json(tmp_path):
    from pipeline.manual import load_manual

    (tmp_path / "review.json").write_text(
        json.dumps({"manual": {"reach_facebook": 92400}}), encoding="utf-8"
    )
    assert load_manual(tmp_path)["reach_facebook"] == 92400


def test_nested_paths_are_edited():
    """A böngészőben a `key_finding.title` is szerkeszthető — pontozott útvonal."""
    narrative = {"key_finding": {"title": "Eredeti", "body": "Törzs"}}
    edited = apply_edits(narrative, {"key_finding.title": "Átírt"})
    assert edited["key_finding"]["title"] == "Átírt"
    assert edited["key_finding"]["body"] == "Törzs"


def test_editing_does_not_mutate_the_original():
    narrative = {"key_finding": {"title": "Eredeti"}}
    apply_edits(narrative, {"key_finding.title": "Átírt"})
    assert narrative["key_finding"]["title"] == "Eredeti"


def test_a_path_that_does_not_exist_is_reported_not_swallowed():
    """A néma elnyelés rosszabb, mint a hiba — a hívó tudja meg, mi maradt ki."""
    from pipeline.review import applied_edits

    narrative = {"executive_summary": "a", "key_finding": {"title": "b"}}
    edits = {"executive_summary": "x", "key_finding.title": "y", "nincs.ilyen": "z"}
    assert set(applied_edits(narrative, edits)) == {
        "executive_summary",
        "key_finding.title",
    }


def test_a_list_block_cannot_be_replaced_by_a_string():
    narrative = {"next_steps": ["a", "b"]}
    assert apply_edits(narrative, {"next_steps": "egyetlen szöveg"})["next_steps"] == [
        "a",
        "b",
    ]


def _as_template(markup: str) -> str:
    """Amit a böngészőben a review.js csinál: sablon vissza a megjelenített HTML-ből."""
    import html as html_module
    import re

    parts = []
    for match in re.finditer(
        r'<span[^>]*data-ref="([^"]+)"[^>]*>.*?</span>|([^<]+)', markup
    ):
        parts.append(match.group(1) or match.group(2))
    return html_module.unescape("".join(parts))


def test_the_edit_round_trip_preserves_the_template():
    """A menedzser a megjelenített szöveget látja; a mentésnek a sablont kell
    visszaadnia.

    Enélkül a behelyettesített számok kerülnének vissza a narrative.json-be, és
    a következő build a saját narratíváját utasítaná el a számjegy-tilalom
    miatt — egyetlen szerkesztés tönkretenné a riportot.
    """
    import json
    from pathlib import Path

    from pipeline.narrative import resolve_all

    base = Path(__file__).parent / "fixtures" / "larus-2026-07"
    data = json.loads((base / "report_data.golden.json").read_text(encoding="utf-8"))
    narrative = json.loads((base / "narrative.json").read_text(encoding="utf-8"))

    rendered = resolve_all(narrative, data, markup=True)["executive_summary"]
    recovered = _as_template(rendered)

    assert recovered == narrative["executive_summary"]


def test_an_edited_block_still_renders():
    """Szerkesztés után is fel kell oldódnia — a hivatkozások megmaradnak."""
    import json
    from pathlib import Path

    from pipeline.narrative import resolve_all

    base = Path(__file__).parent / "fixtures" / "larus-2026-07"
    data = json.loads((base / "report_data.golden.json").read_text(encoding="utf-8"))
    narrative = json.loads((base / "narrative.json").read_text(encoding="utf-8"))

    recovered = _as_template(
        resolve_all(narrative, data, markup=True)["executive_summary"]
    )
    edited = apply_edits(narrative, {"executive_summary": "Bevezető. " + recovered})

    out = resolve_all(edited, data)["executive_summary"]
    assert out.startswith("Bevezető. ")
    assert "472,71 EUR" in out


def test_list_items_are_editable_by_index():
    """A „mi működött" pontjait is át lehet írni a böngészőben."""
    narrative = {"what_worked": ["első", "második"], "next_steps": ["lépés"]}
    edited = apply_edits(
        narrative, {"what_worked.1": "átírt második", "next_steps.0": "átírt lépés"}
    )
    assert edited["what_worked"] == ["első", "átírt második"]
    assert edited["next_steps"] == ["átírt lépés"]


def test_an_index_beyond_the_list_is_reported_not_swallowed():
    from pipeline.review import applied_edits

    narrative = {"what_worked": ["egy"]}
    assert applied_edits(narrative, {"what_worked.5": "x"}) == []


def test_a_list_index_cannot_create_an_element():
    narrative = {"what_worked": ["egy"]}
    assert apply_edits(narrative, {"what_worked.3": "x"})["what_worked"] == ["egy"]
