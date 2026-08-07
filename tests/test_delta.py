import json
from pathlib import Path

import pytest

from pipeline.render import _signed, render

GOLDEN = Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"


@pytest.fixture
def data():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture
def compared(tmp_path):
    """A fixture-ben nincs previous.json, tehát nincs mihez mérni. Az összeha-
    sonlító oldalt csak úgy tudjuk megnézni, ha adunk neki előző hónapot."""
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    data["comparison"] = {
        "facebook": {
            "visits": {"now": 1525, "before": 1113, "diff": 412, "pct": 37.0},
            "interactions": {"now": 255, "before": 342, "diff": -87, "pct": -25.4},
            "follows": {"now": 5, "before": 5, "diff": 0, "pct": 0.0},
        }
    }
    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def test_growth_and_decline_get_opposite_arrows(compared):
    assert 'class="delta delta--up" aria-label="növekedés">↑' in compared
    assert 'class="delta delta--down" aria-label="csökkenés">↓' in compared


def test_both_directions_use_the_same_colour():
    """Az irányt a nyíl mutatja, nem a szín. Egy csökkenést pirosra festeni
    ítélet volna — nem minden visszaesés rossz hír."""
    from pipeline.render import stylesheet

    css = stylesheet()
    assert ".delta { color: var(--brand-rose)" in css
    assert "delta--down" not in css, "az iránynak nincs saját színe"


def test_an_unchanged_value_gets_no_arrow(compared):
    """Gondolatjel volt itt, és mínuszjelnek látszott: úgy tűnt, mintha
    csökkent volna, pedig épp hogy nem mozdult."""
    assert 'aria-label="változatlan">○' in compared
    assert "változatlan\">–" not in compared


def test_the_change_is_shown_with_its_sign_next_to_the_headline(compared):
    """A nyíl iránya önmagában nem elég. Ha a szám mellől hiányzik a
    mínuszjel, egy csökkenés növekedésnek olvasható."""
    assert 'class="delta-value"' in compared
    assert "−87" in compared


def test_the_headline_can_show_the_change_instead_of_the_result(data, tmp_path):
    """Kampányriportnál nem az a kérdés, hol tartunk, hanem hogy mennyit
    mozdult. A menedzser ezt megjegyzésben kéri, ezért kapcsoló."""
    from pipeline.render import render

    data["meta"]["comparison_headline"] = "change"
    data["comparison"] = {
        "facebook": {"visits": {"now": 1525, "before": 1113, "diff": 412, "pct": 37.0}}
    }
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")

    assert "Felkeresések változása" in html
    assert "1 525 a hónapban".replace(" ", "\xa0") in html.replace(" ", "\xa0")


def test_unchanged_and_unknown_are_not_the_same_sign(compared):
    """A „mértük és nem mozdult” meg a „nincs mihez mérni” két különböző dolog.
    Egy jellel a kettő egybemosódna, és az adathiány úgy nézne ki, mint egy
    mért nulla."""
    from pipeline.render import stylesheet

    assert 'class="delta delta--flat"' in compared
    assert 'class="delta delta--none"' not in compared, "van összehasonlítási alap"

    css = stylesheet()
    assert ".delta--flat { color: var(--ink-soft)" in css
    assert ".delta--none { color: var(--rule)" in css


def test_the_arrow_does_not_touch_the_number():
    """Szóköz nélkül a nyíl tizedesjel benyomását kelti."""
    from pipeline.render import stylesheet

    assert "margin-right: .12em" in stylesheet()


def test_the_change_is_written_out_with_its_sign(compared):
    assert "+412" in compared
    assert "−87" in compared, "valódi mínuszjel, nem kötőjel"


def test_the_minus_sign_is_not_a_hyphen():
    """Kötőjellel egy csökkenés úgy néz ki, mintha növekedés volna."""
    assert _signed(-87) == "−87"
    assert _signed(412) == "+412"
    assert _signed(0) == "0"
    assert "-" not in _signed(-87)


def test_the_follower_movement_uses_the_same_indicator(compared):
    """Egy szabály, egy definíció — a követőszám mozgása se lógjon ki."""
    assert "+5 a hónapban" in compared
