"""Kézzel bevitt értékek.

Vannak számok, amiket a Meta nem exportál, de a felületén ott vannak (havi
deduplikált elérés, követő-összlétszám). Ezeket a menedzser olvassa le és írja be.

Az elv: **ami hiányzik, de beszerezhető, az látható marad.** Ha csendben
kihagynánk, a menedzser sosem tudná meg, hogy létezik ilyen adat. Ezért a
riportban megjelenik a hely, azzal együtt, hogy honnan szerezhető be.
"""

from pathlib import Path

SLOTS = {
    "reach_facebook": {
        "label": "Facebook havi elérés",
        "hint": "Business Suite → Elérés csempe, havi időszakra állítva",
    },
    "reach_instagram": {
        "label": "Instagram havi elérés",
        "hint": "Business Suite → Elérés csempe, havi időszakra állítva",
    },
}
# A követőszám nem itt van: a `client.yaml` kéri be, a munka elején. Kitölthető
# mezőként a riport végén állt, és pont ezért maradt mindig üresen — oda már
# senki nem megy vissza. Lásd `bootstrap.FOLLOWER_HINT`.


def load_manual(directory: Path) -> dict:
    """A kézi értékek a `review.json` `manual` szakaszában élnek — egy fájl,
    egy mentés gomb."""
    from pipeline.review import load_review

    return load_review(directory)["manual"]
