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


def apply_edits(narrative: dict, edits: dict) -> dict:
    """Meglévő szöveges blokkok felülírása. Új blokkot a review nem hozhat létre."""
    return {
        key: edits.get(key, value) if isinstance(value, str) else value
        for key, value in narrative.items()
    }
