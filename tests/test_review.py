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
