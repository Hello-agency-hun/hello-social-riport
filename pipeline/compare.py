"""Összehasonlítás az előző időszakkal.

Forrása a hónap mappájában lévő `previous.json` — legegyszerűbben az előző havi
`report_data.json` átmásolva. Ha nincs, az összehasonlító oldal akkor is
megjelenik, de kitölthető mezőkkel: az érték létezik, csak még nincs meg.
Kitalált változást soha nem közlünk.
"""

import json
from pathlib import Path


def load_previous(directory: Path) -> dict | None:
    path = Path(directory) / "previous.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def deltas(now: dict, before: dict) -> dict:
    """Csak azokra a metrikákra, amelyek mindkét időszakban szerepelnek."""
    result = {}
    for key, value in now.items():
        if key not in before:
            continue
        previous = before[key]
        diff = value - previous
        result[key] = {
            "now": value,
            "before": previous,
            "diff": diff,
            "pct": round(diff / previous * 100, 1) if previous else None,
        }
    return result
