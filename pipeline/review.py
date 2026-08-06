"""A review-kör: amit a menedzser a böngészőben átír, ide kerül vissza.

Egyetlen fájl (`review.json`) tartja a kézi számokat, a szövegjavításokat és a
megjegyzéseket — a menedzsernek egy gombot kell megnyomnia, nem hármat.

A javított szöveg **ugyanazon a számjegy-ellenőrzésen megy át**, mint amit a
modell írt: a review-kör nem kiskapu.
"""

import json
from pathlib import Path

SECTIONS = {"manual": dict, "edits": dict, "comments": list}


def load_review(directory: Path) -> dict:
    path = Path(directory) / "review.json"
    stored = {}
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
    return {key: stored.get(key) or kind() for key, kind in SECTIONS.items()}


def _leaf(narrative, path: str):
    """A pontozott útvonal létező **szöveges** levele: `(tároló, kulcs)` vagy `None`.

    Kezel beágyazott szótárat (`key_finding.title`) és listaelemet is
    (`what_worked.0`) — a böngészőben mindkettő szerkeszthető. Nem szöveges
    vagy nem létező levélre nem írunk: a review nem hozhat létre új blokkot,
    és nem cserélhet listát szövegre.
    """

    def step(container, part: str):
        if isinstance(container, list):
            if not part.isdigit() or int(part) >= len(container):
                return None, None
            return container, int(part)
        if isinstance(container, dict) and part in container:
            return container, part
        return None, None

    parts = path.split(".")
    current = narrative
    for part in parts[:-1]:
        container, key = step(current, part)
        if container is None:
            return None
        current = container[key]

    container, key = step(current, parts[-1])
    if container is None or not isinstance(container[key], str):
        return None
    return container, key


def applied_edits(narrative: dict, edits: dict) -> list[str]:
    """Amelyik javítás tényleg érvényesül. A többiről a hívó számoljon be."""
    return [path for path in edits if _leaf(narrative, path)]


def apply_edits(narrative: dict, edits: dict) -> dict:
    """Meglévő szöveges blokkok felülírása. Új blokkot a review nem hozhat létre."""
    import copy

    updated = copy.deepcopy(narrative)
    for path, text in edits.items():
        found = _leaf(updated, path)
        if found:
            parent, key = found
            parent[key] = text
    return updated
