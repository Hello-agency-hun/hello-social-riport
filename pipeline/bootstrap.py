"""A `client.yaml` kitöltése abból, ami az exportokban már benne van.

Az oldalazonosítót eddig a menedzsertől kértük — miközben ott áll a Tartalom
export minden során. Aki nem éri el a Business Suite-ot (és a menedzserek egy
része nem éri el), az az első lépésnél elakadt, pedig a válasz a kezében volt.

Amit nem tudunk kiolvasni, azt nem találjuk ki: az placeholderként marad benn,
és megmondja, honnan szerezhető meg.
"""

import csv
import io
from pathlib import Path

from pipeline.detect import scan
from pipeline.textio import read_text

PLACEHOLDERS = {
    "name": "<Ügyfél neve — ahogy a riport címlapján szerepeljen>",
    "fb_page_id": "<Business Suite → Beállítások → Oldalazonosító>",
    "fb_page_name": "<a Facebook-oldal pontos neve>",
    "ig_handle": "<instagram felhasználónév, @ nélkül — a profil URL végéről>",
    "contact_email": "<ugyfel>@helloagency.hu",
    "currency": "EUR",
}

# A követőszám egyik exportban sincs benne — a `Követők.csv` napi *új* követést
# ad, nem az állományt —, viszont bárki leolvassa a profilról fél perc alatt.
# Ezért nem kitölthető mezőként várjuk a riport végén, ahol elsikkad, hanem itt
# kérjük be, a munka elején: enélkül a növekedés nem számolható ki.
FOLLOWER_HINT = {
    "facebook": "a Facebook-oldal fejlécében, vagy Business Suite → Közönség",
    "instagram": "az Instagram-profil fejlécében",
}


def _first_row(path: Path) -> dict[str, str]:
    reader = csv.DictReader(io.StringIO(read_text(path), newline=""))
    return next(reader, {}) or {}


def _from_content(path: Path) -> dict[str, str]:
    row = _first_row(path)
    page_id = (row.get("Oldalazonosító") or "").strip()
    page_name = (row.get("Oldal neve") or "").strip()
    found = {}
    if page_id:
        found["fb_page_id"] = page_id
    if page_name:
        # Az oldal neve és az ügyfél neve a gyakorlatban ugyanaz. Ha mégsem,
        # a menedzser átírja — de üresen hagyva biztosan elfelejtené.
        found["fb_page_name"] = page_name
        found["name"] = page_name
    return found


def _from_ads(path: Path) -> dict[str, str]:
    from pipeline.parsers.meta_ads import detect_currency

    header = next(csv.reader(io.StringIO(read_text(path), newline="")), [])
    currency = detect_currency(header)
    return {"currency": currency} if currency else {}


def suggest(input_dir) -> dict[str, str]:
    """Amit az `input/` mappából ki tudunk olvasni. Sosem dob hibát."""
    directory = Path(input_dir)
    if not directory.is_dir():
        return {}

    found: dict[str, str] = {}
    try:
        sources = scan(directory)
    except Exception:
        return {}

    for source in sources:
        try:
            if source.kind == "meta_content":
                found.update(_from_content(source.path))
            elif source.kind == "meta_ads":
                found.update(_from_ads(source.path))
        except Exception:
            # A bootstrap akkor fut, amikor a menedzser már hibahelyzetben van.
            # Ha ő maga is elszáll, elveszi az egyetlen segítséget is.
            continue
    return found


def template(found: dict[str, str]) -> str:
    values = {key: found.get(key) or default for key, default in PLACEHOLDERS.items()}
    return (
        "client:\n"
        f'  name: "{values["name"]}"\n'
        f'  fb_page_id: "{values["fb_page_id"]}"\n'
        f'  fb_page_name: "{values["fb_page_name"]}"\n'
        f'  ig_handle: "{values["ig_handle"]}"\n'
        "  # A záróoldal kapcsolati címe. Ügyfelenként külön postafiók van;\n"
        "  # ha nem adod meg, a mappanévből tippelek (<mappa>@helloagency.hu).\n"
        f'  contact_email: "{values["contact_email"]}"\n'
        "\n"
        "# Követőszám a hónap végén — a profilról olvasható le.\n"
        "followers:\n"
        f"  facebook: <{FOLLOWER_HINT['facebook']}>\n"
        f"  instagram: <{FOLLOWER_HINT['instagram']}>\n"
        "\n"
        "report:\n"
        "  language: hu\n"
        f"  currency: {values['currency']}\n"
    )
