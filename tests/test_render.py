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


def test_key_numbers_appear(html):
    assert "4 312" in html
    assert "130" in html
    assert "472" in html


def test_unmatched_boosts_are_disclosed(html):
    """Ami nem mérhető, azt a riport kimondja — nem hallgatja el."""
    assert "nem illesztett" in html.lower()


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
