"""Az agent-útmutatók nem csúszhatnak el a repótól.

A `SKILL.md`-t a Claude Code olvassa, az `AGENTS.md`-t a Codex és a többi
agent. Két leírás ugyanarról a munkáról óhatatlanul szétcsúszik — ez a repóban
egyszer már megtörtént: a mappaábra két helyen szerepelt, és az egyik rossz
helyre tette a `client.yaml`-t. Emberi szemmel ez nem tűnik fel, mert mindkettő
hihetően néz ki.

Ezért az `AGENTS.md` nem másolat, hanem útvonaljelző — és amire mutat, annak
léteznie kell.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
SKILL = ROOT / "skills" / "hello-report" / "SKILL.md"

# `[felirat](utvonal)` — a horgonyokat és a külső hivatkozásokat kihagyjuk.
LINK = re.compile(r"\[[^\]]+\]\((?!https?://|#)([^)]+)\)")


def _links(path: Path) -> list[str]:
    return LINK.findall(path.read_text(encoding="utf-8"))


def test_both_agent_entry_points_exist():
    """Mindkét platform belépési pontja megvan."""
    assert AGENTS.exists(), "Codex és a többi agent ezt olvassa"
    assert SKILL.exists(), "a Claude Code ezt olvassa"


@pytest.mark.parametrize("doc", [AGENTS, SKILL], ids=["AGENTS.md", "SKILL.md"])
def test_every_referenced_file_exists(doc):
    """Egy útmutató, ami nem létező fájlra mutat, rosszabb a semminél: az agent
    keresgél, aztán kitalál valamit helyette."""
    for target in _links(doc):
        assert (ROOT / target).exists(), f"{doc.name} → nincs ilyen fájl: {target}"


def test_agents_points_at_the_skill_instead_of_repeating_it():
    """Az AGENTS.md útvonaljelző, nem második leírás. Ha egyszer teljes
    eljárássá hízik, a két fájl elkezd szétcsúszni."""
    text = AGENTS.read_text(encoding="utf-8")

    assert "skills/hello-report/SKILL.md" in text, "mutasson a valódi eljárásra"
    assert len(text) < len(SKILL.read_text(encoding="utf-8")) * 2, (
        "az AGENTS.md túl nagyra nőtt — valószínűleg átmásolta a SKILL.md-t, "
        "ahelyett hogy odamutatna"
    )


def test_the_sandbox_escape_hatch_is_documented():
    """A Codex sandbox alapból hálózat nélkül fut, a kreatívok viszont
    letöltésre kerülnek. Enélkül az első futás érthetetlen hibával áll meg."""
    text = AGENTS.read_text(encoding="utf-8")

    assert "--offline" in text
    assert "hálózat" in text, "mondjuk meg, mikor kell"
    # …és azt is, hogy ez nem az ügyfélnek szánt riport
    assert "helyőrző" in text


def test_the_unbreakable_rules_are_named_for_agents_that_never_see_the_skill():
    """Ha az agent csak az AGENTS.md-ig jut, a három szabályt akkor is tudnia
    kell — különben a hibaüzenetek értelmetlennek látszanak neki."""
    text = AGENTS.read_text(encoding="utf-8")

    assert "nem írhatsz számot" in text
    assert "nem becsülsz meg" in text
    assert "nem nevezed át" in text
