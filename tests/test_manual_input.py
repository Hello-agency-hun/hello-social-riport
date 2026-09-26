"""A kézi beviteli mező számolvasása.

Ez JavaScript, tehát a szabályt itt a forrásra nézve rögzítjük. A tényleges
viselkedést böngészőben mértük ki; a teszt azt őrzi, hogy a javítás ne
kopjon vissza.
"""

import re
from pathlib import Path

_SOURCE = (
    Path(__file__).resolve().parent.parent / "templates" / "review.js"
).read_text(encoding="utf-8")

# A kommentek nélkül nézzük: a régi, hibás mintát a magyarázat is tartalmazza,
# és arra nem szabad elbuknia az ellenőrzésnek.
REVIEW_JS = "\n".join(
    line for line in _SOURCE.splitlines() if not line.strip().startswith("//")
)


def test_the_minus_sign_is_no_longer_stripped():
    """`replace(/[^0-9]/g, "")` volt itt, ami letörölte a mínuszjelet: aki
    „-87”-et írt be, 87-et kapott, néma előjelváltással. Egy csökkenés
    növekedésként került volna az ügyfélhez."""
    assert '/[^0-9]/g' not in REVIEW_JS, "ez a minta törli az előjelet"
    assert "readNumber" in REVIEW_JS


def test_negative_and_percentage_input_is_accepted():
    """A menedzser az első hónapban az előző havi értékeket írja be, és ott
    lehet csökkenés is. A Business Suite csempéiről pedig százalékot olvas le."""
    reader = REVIEW_JS[REVIEW_JS.index("function readNumber") :]
    reader = reader[: reader.index("\n  }")]

    assert '"%"' in reader or "'%'" in reader, "százalékjel elfogadva"
    assert '","' in reader or "','" in reader, "magyar tizedesvessző elfogadva"
    assert "−" in reader, "a valódi mínuszjel is előjel, nem szemét"
    assert "-?" in reader, "az előjel része a mintának"


def test_a_non_number_is_rejected_rather_than_coerced():
    """Korábban minden nem-számjegy egyszerűen eltűnt, tehát a „kb. 12 ezer”
    beírásból 12 lett. Most vagy szám, vagy semmi."""
    reader = REVIEW_JS[REVIEW_JS.index("function readNumber") :]
    assert "return null" in reader


def test_applied_manual_values_survive_later_review_rounds():
    """Az újrarenderelt összehasonlító kártyának már nincs ``data-manual``
    mezője. A következő mentés ezért a korábbi értékekből induljon, különben
    egy puszta narratívajavítás kitörli az előző havi számokat."""
    collector = REVIEW_JS[REVIEW_JS.index("function collect") :]
    collector = collector[: collector.index("var edits")]

    assert "Object.assign({}, stored.manual || {})" in collector
    assert "delete manual[field.dataset.manual]" in collector


def test_review_js_keeps_line_breaks():
    r"""A böngészőoldali gyűjtés sem moshatja el a sortörést.

    Az `asTemplate` korábban `\s+`-t vont össze egyetlen szóközzé — a `\s`
    pedig a sortörést is jelenti. Így a mentés pillanatában elveszett minden
    Enter, még mielőtt a szerverhez ért volna.
    """
    source = (
        Path(__file__).resolve().parent.parent / "templates" / "review.js"
    ).read_text(encoding="utf-8")

    assert r"/\s+/g" not in source, "a sortörést is összevonó minta"
    assert "BR" in source, "a <br> elemet külön kell kezelni"
    assert "\n" in source, "sortörést kell kiírnia"


def test_review_js_has_no_broken_string_literals():
    """A `review.js` sablonba nem kerülhet nyers sortörés idézőjelek közé.

    Egy szerkesztésnél pontosan ez történt: a `"\n"` helyére valódi sortörés
    került, a fájl megszűnt értelmezhető JavaScriptnek lenni, és a riport
    szerkesztője némán meghalt volna a böngészőben. A tesztek ezt nem vették
    észre, mert a Python-oldalt nem érintette.
    """
    source = (
        Path(__file__).resolve().parent.parent / "templates" / "review.js"
    ).read_text(encoding="utf-8")

    for number, line in enumerate(source.splitlines(), start=1):
        # A kommentekben magyar idézőjel is állhat, azokat nem vizsgáljuk.
        if line.lstrip().startswith("//"):
            continue
        without_escapes = line.replace('\\"', "").replace("\\\\", "")
        assert without_escapes.count('"') % 2 == 0, (
            f"{number}. sor: páratlan idézőjel — nyers sortörés a stringben?\n{line}"
        )


def test_browser_storage_is_scoped_to_one_report():
    """A tárhely eredetenként közös. Egy közös kulccsal az egyik ügyfél kézi
    adatai és megjegyzései a másik ügyfél review.json-jába kerültek, ha a
    riportokat ugyanarról a szerverről nyitották meg."""
    assert 'var KEY = "hello-report-review";' not in REVIEW_JS
    assert '"hello-report-review:" + (REPORT.key' in REVIEW_JS
    assert "window.__helloReport" in REVIEW_JS


def test_a_processed_rounds_comments_are_not_sent_again():
    """Az újrarenderelt riport új revíziót kap; a régi kör megjegyzései nem
    kerülhetnek bele a következő review.json-ba."""
    assert "stored.revision === REVISION" in REVIEW_JS


def test_unsaved_edits_survive_a_reload_but_never_overwrite_newer_text():
    """Újratöltés után a javítás visszakerül a lapra — de csak akkor, ha
    ugyanarra a szövegre készült, ami most a lapon áll. Egy újrarenderelt
    riport (az agent közben továbbírta) szövegét a régi javítás nem írhatja
    felül."""
    assert "function restore" in REVIEW_JS
    assert "(stored.bases || {})[path] === block.dataset.original" in REVIEW_JS


def test_a_blocked_storage_does_not_kill_the_editor():
    """Privát ablakban a `localStorage` kivételt dob. Korábban ettől az egész
    szerkesztő leállt, gombok nélkül."""
    loader = REVIEW_JS[REVIEW_JS.index("function load") :]
    loader = loader[: loader.index("\n  }")]
    assert "try" in loader and "catch" in loader
    assert REVIEW_JS.count("localStorage.") == REVIEW_JS.count("localStorage.getItem") + REVIEW_JS.count("localStorage.setItem")


def test_a_zero_manual_value_is_restored():
    """A beírt nulla is érték — a korábbi `if (saved)` elhagyta."""
    assert "if (saved) input.textContent = saved;" not in REVIEW_JS
