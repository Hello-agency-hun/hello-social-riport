"""Kézzel bevitt értékek.

Vannak számok, amiket a Meta nem exportál, de a felületén ott vannak (havi
deduplikált elérés, követő-összlétszám). Ezeket a menedzser olvassa le és írja be.

Az elv: **ami hiányzik, de beszerezhető, az látható marad.** Ha csendben
kihagynánk, a menedzser sosem tudná meg, hogy létezik ilyen adat. Ezért a
riportban megjelenik a hely, azzal együtt, hogy honnan szerezhető be.
"""

from pathlib import Path

# A riport oldalain nincs több üres, szaggatott doboz. Két okból:
#
# 1. Ami mérve van, azt mutatjuk meg — a havi elérés helyén most a poszt-elérés
#    és a megtekintés áll, pontos névvel. Az ügyfél így nem üres helyet lát,
#    hanem adatot.
# 2. Ami nincs mérve, de beszerezhető (havi deduplikált elérés, követőszám), azt
#    a `client.yaml` kéri be, és a `--validate` sorolja fel. Ott a menedzser
#    látja, nem az ügyfél.
#
# Kitölthető mezőként a riport végén álltak, és pont ezért maradtak mindig
# üresen: oda már senki nem ment vissza.
SLOTS: dict[str, dict] = {}

# Ami beszerezhető, de nem exportálható. A `--validate` ebből sorolja fel, mi
# hiányzik még — a menedzsernek, nem az ügyfélnek.
    # A csempe neve csatornánként MÁS, és ez félrevezet. A Facebookon nincs
    # „Elérés” csempe: ott ugyanezt „Nézők” néven adja a Meta („azon Meta-fiókok
    # száma, amelyek legalább egyszer megnézték a tartalmaidat”). Aki az Elérést
    # keresi, nem találja, és a rossz csempét („Megtekintések”) hozza el —
    # az viszont megjelenést mér, nem embert, és nagyságrenddel nagyobb.
FIND_MONTHLY_REACH = {
    "facebook": "Business Suite → Eredmények → **Nézők** csempe, a hónapra "
    "állítva. A Facebookon ez az elérés neve — „Elérés” csempe nincs, a "
    "„Megtekintések” pedig mást mér (megjelenést, nem embert).",
    "instagram": "Business Suite → Eredmények → **Elérés** csempe, a hónapra "
    "állítva.",
}

OBTAINABLE = {
    "monthly_reach": {
        "label": "havi elérés",
        "hint": FIND_MONTHLY_REACH,
        "why": "ez az egyetlen szám, amit semmiből nem lehet kiszámolni: az "
        "elérés emberben mér, és aki két napon látott minket, egy ember — "
        "a napi vagy poszt-szintű értékek összege mindig több a valóságnál "
        "(júliusban a napi Nézők összege ~248 E volt, a havi érték 139,7 E)",
    },
}


def load_manual(directory: Path) -> dict:
    """A kézi értékek a `review.json` `manual` szakaszában élnek — egy fájl,
    egy mentés gomb."""
    from pipeline.review import load_review

    return load_review(directory)["manual"]
