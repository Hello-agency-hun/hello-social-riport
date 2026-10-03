"""Összehasonlítás az előző időszakkal.

Forrása a hónap mappájában lévő `previous.json` — legegyszerűbben az előző havi
`report_data.json` átmásolva. Ha nincs, az összehasonlító oldal akkor is
megjelenik, de kitölthető mezőkkel: az érték létezik, csak még nincs meg.
Kitalált változást soha nem közlünk.
"""

import json
from datetime import date
from pathlib import Path


def load_previous(directory: Path) -> dict | None:
    path = Path(directory) / "previous.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def coverage_check(previous: dict | None, meta: dict) -> dict:
    """Illeszkedik-e az előző havi adat a mostanihoz?

    Ez a Mammut-próba tanulsága. Az ott kapott júniusi riport metrikánként más
    napon zárult (huszonegyedike és harmincegyedike között szórt), a mi júliusi
    adatunk viszont hónap végéig mért. A kettőből képzett „változás" nem
    változás volt, hanem **mérési különbség** — és ez sehol nem látszott volna.

    Négy eset van, és mind mást jelent:

    - `ok` — az előző időszak közvetlenül a mostani előtt zárul
    - `gap` — nap(ok) hiányoznak a kettő között
    - `overlap` — az előző időszak belelóg a mostaniba
    - `unknown` — az előző adat nem mondja meg, mit fed le (PDF-import, régi
      riport). Ilyenkor nem állítjuk, hogy illeszkedik; azt sem, hogy nem.
    """
    if not previous:
        return {"status": "none"}

    before = previous.get("meta") or {}
    prev_end = before.get("measurement_end") or before.get("coverage_end")
    now_start = meta.get("measurement_start") or meta.get("coverage_start")

    if not prev_end or not now_start:
        return {
            "status": "unknown",
            "message": "az előző havi adat nem mondja meg, milyen időszakot fed "
            "le. Ha kézi riportból vagy PDF-ből származik, a belőle számolt "
            "változás lehet, hogy nem változás, hanem mérési különbség.",
        }

    gap = (date.fromisoformat(now_start) - date.fromisoformat(prev_end)).days
    if gap == 1:
        return {"status": "ok", "previous_end": prev_end}
    if gap > 1:
        return {
            "status": "gap",
            "previous_end": prev_end,
            "message": f"{gap - 1} nap hiányzik a két időszak között "
            f"({prev_end} után a következő mért nap {now_start}). A változás "
            "ezekkel a napokkal nem számol.",
        }
    return {
        "status": "overlap",
        "previous_end": prev_end,
        "message": f"a két időszak átfed: az előző {prev_end}-ig tart, a "
        f"mostani {now_start}-tól. Az átfedő napok mindkét oldalon szerepelnek, "
        "tehát a változás kisebbnek látszik a valóságosnál.",
    }


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


def previous_from_manual(manual: dict, channel: str, fields) -> dict:
    """Kézzel bevitt előző havi értékek.

    Az első hónapban nincs `previous.json`. A riport ilyenkor sem hagyja ki az
    összehasonlító oldalt: kitölthető mezőket mutat `prev_<csatorna>_<metrika>`
    kulccsal, és a menedzser beírt értékei innen kerülnek vissza a számításba.
    """
    return {
        field: manual[f"prev_{channel}_{field}"]
        for field in fields
        if f"prev_{channel}_{field}" in manual
    }


def validated_manual_baseline(manual: dict, channels: dict) -> tuple[dict, str | None]:
    """Return manual previous values unless the current month was copied in.

    A Rejuran review exposed a characteristic form error: almost every
    ``prev_*`` value exactly equalled the current channel, while one Instagram
    value equalled Facebook's current total. Those values produce plausible
    percentages, but are not a previous period. We therefore suppress the
    complete manual baseline when several independent exact copies prove that
    the form was populated from the current report.
    """
    resolved = {}
    self_copies = 0
    self_copy_channels = set()
    cross_copies = 0
    current_by_field = {}
    for channel, block in channels.items():
        for field, value in (block.get("totals") or {}).items():
            if isinstance(value, (int, float)):
                current_by_field.setdefault(field, {})[channel] = value

    for channel, block in channels.items():
        totals = block.get("totals") or {}
        for field in totals:
            key = f"prev_{channel}_{field}"
            if key not in manual:
                continue
            value = manual[key]
            resolved.setdefault(channel, {})[field] = value
            if value == totals.get(field):
                self_copies += 1
                self_copy_channels.add(channel)
            elif any(
                other != channel and value == other_value
                for other, other_value in current_by_field.get(field, {}).items()
            ):
                cross_copies += 1

    if (
        (self_copies >= 3 and len(self_copy_channels) >= 2)
        or (self_copies >= 2 and cross_copies >= 1)
    ):
        return {}, (
            "A kézzel megadott előző havi alap gyanúsan a mostani riport "
            "értékeit ismétli, ezért nem számoltunk belőle változást."
        )
    return resolved, None
