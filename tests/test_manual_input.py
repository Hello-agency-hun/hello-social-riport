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
