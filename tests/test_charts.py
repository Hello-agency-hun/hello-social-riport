import re
from datetime import date
from xml.etree import ElementTree

import pytest

from pipeline.charts import bar_chart, donut, line_chart

SERIES = [(date(2026, 7, day), day * 3) for day in range(1, 32)]
BARS = [("Séfünk ajánlata", 9046), ("Gambas Pil-Pil", 4142), ("Frissen", 2068)]


def _parse(svg: str):
    # Stdlib parser szándékosan: a bemenet a charts.py saját, ugyanebben a
    # tesztben generált kimenete — nincs külső entitás és nincs idegen adat.
    # A riport futásidőben soha nem parse-ol XML-t.
    return ElementTree.fromstring(svg)


@pytest.mark.parametrize(
    "svg",
    [
        line_chart(SERIES, label="Hivatkozáskattintások"),
        bar_chart(BARS, label="Elérés"),
        donut([("Fizetett", 17246), ("Organikus", 1565)], label="Elérés megoszlása"),
    ],
)
def test_output_is_well_formed_svg(svg):
    root = _parse(svg)
    assert root.tag.endswith("svg")
    assert root.get("viewBox")
    assert root.get("role") == "img"
    assert root.get("aria-label")


@pytest.mark.parametrize(
    "svg",
    [
        line_chart(SERIES, label="x"),
        bar_chart(BARS, label="x"),
        donut([("a", 3), ("b", 1)], label="x"),
    ],
)
def test_colours_come_from_tokens_not_hardcoded_hex(svg):
    """Ha az akcentus változik a brand.css-ben, a chartoknak követniük kell."""
    assert "var(--" in svg
    assert not re.search(r"#[0-9A-Fa-f]{6}", svg)


def test_line_chart_draws_one_point_per_day():
    svg = line_chart(SERIES, label="x")
    path = _parse(svg).find(".//{http://www.w3.org/2000/svg}polyline")
    assert path is not None
    assert len(path.get("points").split()) == 31


def test_bar_chart_scales_to_the_largest_value():
    svg = bar_chart(BARS, label="x")
    widths = [
        float(rect.get("width"))
        for rect in _parse(svg).iter("{http://www.w3.org/2000/svg}rect")
        if rect.get("class") == "bar"
    ]
    assert len(widths) == 3
    assert widths == sorted(widths, reverse=True)
    assert widths[0] > widths[-1]


def test_donut_segments_cover_the_full_circle():
    svg = donut([("a", 3), ("b", 1)], label="x")
    circles = [
        c
        for c in _parse(svg).iter("{http://www.w3.org/2000/svg}circle")
        if c.get("class") == "segment"
    ]
    assert len(circles) == 2


def test_empty_data_renders_a_placeholder_not_a_crash():
    """Hiányzó adatnál üres keret és felirat — nem nulla, nem összeomlás."""
    for svg in (line_chart([], label="x"), bar_chart([], label="x"), donut([], label="x")):
        root = _parse(svg)
        assert root.tag.endswith("svg")
        assert "nincs adat" in svg


def test_single_point_series_does_not_divide_by_zero():
    svg = line_chart([(date(2026, 7, 1), 5)], label="x")
    assert _parse(svg).tag.endswith("svg")


def test_donut_with_zero_total_does_not_divide_by_zero():
    svg = donut([("a", 0), ("b", 0)], label="x")
    assert "nincs adat" in svg
