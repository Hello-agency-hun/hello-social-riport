import json
from pathlib import Path

import pytest

from pipeline.manual import SLOTS, load_manual

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)


def test_missing_file_yields_an_empty_mapping(tmp_path):
    assert load_manual(tmp_path) == {}


def test_values_are_read_from_manual_json(tmp_path):
    (tmp_path / "manual.json").write_text(
        json.dumps({"reach_facebook": 92400}), encoding="utf-8"
    )
    assert load_manual(tmp_path)["reach_facebook"] == 92400


def test_every_slot_says_where_to_get_it():
    """A mező önmagában semmit nem ér — meg kell mondania, honnan szerezhető be."""
    for key, slot in SLOTS.items():
        assert slot["label"], key
        assert slot["hint"], f"{key}: nincs megadva, honnan szerezhető be"


@pytest.fixture
def data():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture
def empty(data, tmp_path):
    from pipeline.render import render

    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def test_empty_slot_is_visible_on_screen(empty):
    assert 'data-manual="reach_facebook"' in empty
    assert "Business Suite" in empty


def test_empty_slot_is_hidden_when_printing(empty):
    css = empty[empty.index("<style>") : empty.index("</style>")]
    printed = css[css.index("@media print") :]
    assert ".manual-slot" in printed and "display: none" in printed


def test_filled_slot_renders_as_a_value(data, tmp_path):
    from pipeline.render import render

    html = render(
        data,
        cache_dir=tmp_path,
        fetcher=lambda url: b"",
        manual={"reach_facebook": 92400},
    )
    assert "92 400" in html.replace(" ", " ")
    assert "kézi adat" in html
    assert 'data-manual="reach_facebook"' not in html
