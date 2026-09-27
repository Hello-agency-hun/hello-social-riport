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


def test_donut_legend_uses_a_hungarian_decimal_comma():
    """A riport szövege vesszőt használ; a jelmagyarázat nem térhet el tőle."""
    svg = donut([("a", 917), ("b", 83)], label="x")
    assert "91,7%" in svg
    assert "91.7%" not in svg


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


def test_line_chart_labels_more_than_just_the_maximum():
    """Egyetlen `max` felirat kevés — a görbe legyen önmagában leolvasható."""
    svg = line_chart(SERIES, label="x")
    root = _parse(svg)
    texts = [t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text")]
    # rácsvonal-értékek: nulla, fél, csúcs
    assert "0" in texts
    assert "93" in texts, "a legerősebb nap értéke"
    assert any("összesen" in t for t in texts), "az időszak összege"
    assert len(texts) >= 7


def test_the_three_strongest_days_are_marked():
    """Egy csúcs kevés — ránézésre látszódjon a hónap három legerősebb napja."""
    svg = line_chart(SERIES, label="x")
    circles = list(_parse(svg).iter("{http://www.w3.org/2000/svg}circle"))
    assert len(circles) == 3


def test_peaks_are_spread_out_not_three_days_of_one_spike():
    """Egyetlen kiugrás szomszédos napjait ne címkézzük fel háromszor."""
    from datetime import timedelta

    flat = [(date(2026, 7, 1) + timedelta(days=d), 10) for d in range(31)]
    for d in (9, 10, 11):
        flat[d] = (flat[d][0], 500 - d)
    svg = line_chart(flat, label="x")
    labelled = [
        t.text
        for t in _parse(svg).iter("{http://www.w3.org/2000/svg}text")
        if t.get("font-size") == "10"
    ]
    assert len(labelled) == 3
    assert len(set(labelled)) == 3
    assert labelled.count("07.10.") <= 1


def test_the_peak_label_stays_inside_the_chart_when_the_peak_is_last():
    """Ha a csúcs a jobb szélen van, a felirat befelé fordul, nem lóg ki."""
    rising = [(date(2026, 7, day), day) for day in range(1, 32)]
    svg = line_chart(rising, label="x")
    anchors = [
        t.get("text-anchor")
        for t in _parse(svg).iter("{http://www.w3.org/2000/svg}text")
        if t.get("font-weight") == "700"
    ]
    assert anchors == ["end"]


def test_the_curve_itself_takes_the_given_colour():
    """Nem elég a kitöltést színezni — a vonal maradt volna zöld mindenhol."""
    svg = line_chart(SERIES, label="x", colour="var(--brand-rose)")
    line = _parse(svg).find(".//{http://www.w3.org/2000/svg}polyline")
    assert line.get("stroke") == "var(--brand-rose)"
    assert "var(--accent)" not in svg


def test_peak_labels_do_not_collide():
    """A címkék vízszintes távolsága legyen elég a szöveg szélességéhez."""
    import re as _re

    svg = line_chart(SERIES, label="x")
    xs = sorted(
        float(m) for m in _re.findall(r'<circle cx="([\d.]+)"', svg)
    )
    assert all(b - a >= 60 for a, b in zip(xs, xs[1:])), xs


def _label_ys(svg: str) -> list[float]:
    return [
        float(t.get("y"))
        for t in _parse(svg).iter("{http://www.w3.org/2000/svg}text")
    ]


@pytest.mark.parametrize("peak", [1, 7, 31, 64, 79, 93, 2022, 48213])
def test_every_label_stays_inside_the_drawing(peak):
    """A legerősebb nap pontosan a diagram tetejére esett, és a fölé írt
    dátum kilógott a rajzterületből — épp a hónap csúcsnapjának dátuma nem
    látszott. Minden felirat alapvonala a rajzterületen belül legyen, a
    betűmagassággal együtt."""
    series = [(date(2026, 7, day), peak if day == 21 else peak // 3) for day in range(1, 32)]
    svg = line_chart(series, label="x", height=175)
    assert all(10 <= y <= 175 for y in _label_ys(svg)), _label_ys(svg)


def test_the_axis_uses_round_numbers():
    """`0 · 15 · 31` helyett `0 · 20 · 40`: a görbe ránézésre leolvasható."""
    peaks = [(date(2026, 7, day), 31 if day == 21 else 3) for day in range(1, 32)]
    texts = [t.text for t in _parse(line_chart(peaks, label="x")).iter(
        "{http://www.w3.org/2000/svg}text")]
    assert "40" in texts and "20" in texts
    assert "15" not in texts


@pytest.mark.parametrize("peak, top", [(1, 2), (3, 4), (31, 40), (64, 80), (93, 120), (2022, 2500)])
def test_the_axis_top_is_round_even_and_above_the_peak(peak, top):
    from pipeline.charts import _nice_top

    assert _nice_top(peak) == top


def test_english_day_labels_name_the_month():
    """Az angol riportban a `07.21.` nem egyértelmű; a `Jul 21` igen."""
    svg = line_chart(SERIES, label="x", language="en", total_label="total")
    texts = [t.text or "" for t in _parse(svg).iter("{http://www.w3.org/2000/svg}text")]
    assert "Jul 1" in texts and "Jul 31" in texts
    assert not any(text.endswith(".") and text[:2].isdigit() for text in texts)


def test_empty_charts_speak_the_report_language():
    for svg in (
        line_chart([], label="x", empty_label="no data"),
        bar_chart([], label="x", empty_label="no data"),
        donut([], label="x", empty_label="no data"),
    ):
        assert "no data" in svg and "nincs adat" not in svg
