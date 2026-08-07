"""„Így értelmeztem a mappát" — a néma hibák elleni védelem.

A Mammut-próba hét csúszástípusából **négy teljesen néma volt**: a rendszer nem
hibázott, csak rosszul párosított. Az ilyen hiba nem hiányként jelentkezik,
hanem téves értelmezésként — tehát csak úgy fogható meg, ha a rendszer kiírja,
mit hogyan olvasott, MIELŐTT bármit kiszámolna belőle.
"""

import shutil

from pipeline.build import build
from pipeline.cli import _report_map


def test_every_source_says_what_we_made_of_it(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    files = {item["file"] for item in data["inventory"]}

    for source in (fixture_dir / "input").iterdir():
        assert source.name in files, f"{source.name} nincs a leltárban"


def test_a_daily_tile_shows_its_channel_and_total(fixture_dir):
    """A Mammutnál két „Megtekintések" csempe volt, mindkét csatornán ugyanazon
    a néven. Csendben egymásra kerültek volna — a csatorna és az összeg együtt
    ezt ránézésre elárulja."""
    data = build(fixture_dir, period="2026-07")
    tile = next(i for i in data["inventory"] if i["file"].startswith("Megtekintések"))

    assert "instagram" in tile["as"]
    assert "összeg" in tile["detail"]


def test_a_content_export_shows_its_post_counts_per_channel(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    export = next(i for i in data["inventory"] if i["as"] == "Tartalom")

    assert "facebook" in export["detail"]


def test_empty_captions_are_flagged_in_the_inventory(fixture_dir, tmp_path):
    """Ez volt a legsúlyosabb néma hiba: az IG-exportban nincs `Cím` oszlop,
    ezért minden poszt szöveg nélkül jött be. Semmi nem állt meg tőle — csak a
    boost-illesztés hiúsult meg, mert az szöveg alapján megy."""
    from pipeline.textio import read_text

    work = tmp_path / "ures-szoveg"
    shutil.copytree(fixture_dir, work)

    # A poszt-szövegek idézőjelesek és vesszőt is tartalmaznak — naiv
    # daraboláshoz nem nyúlunk, csak a csv modulhoz.
    import csv
    import io

    content = next((work / "input").glob("Jul-01*.csv"))
    rows = list(csv.reader(io.StringIO(read_text(content), newline="")))
    title = rows[0].index("Cím")
    for row in rows[1:]:
        if len(row) > title:
            row[title] = ""

    with content.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)

    data = build(work, period="2026-07")
    export = next(i for i in data["inventory"] if i["as"] == "Tartalom")
    assert "szöveg nélkül" in export["detail"]


def test_the_map_shows_how_many_posts_got_their_spend(fixture_dir):
    """Ha ez nulla, miközben van boost, a párosítás elromlott — és a
    boost-szorzó hamis. A Mammutnál pontosan ez történt."""
    data = build(fixture_dir, period="2026-07")

    assert "posts_with_spend" in data["quality"]
    assert "költéssel" in _report_map(data)


def test_the_interpretation_comes_before_the_numbers(fixture_dir):
    """A sorrend nem esztétika: a menedzsernek azelőtt kell látnia, mit
    olvastunk, hogy elhinné, amit kiszámoltunk."""
    text = _report_map(build(fixture_dir, period="2026-07"))

    assert text.index("Így értelmeztem") < text.index("Organic poszt")
