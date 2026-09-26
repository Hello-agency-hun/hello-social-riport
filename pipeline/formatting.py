"""Számok, összegek és hónapnevek — egy helyen, a riport nyelvén.

Ez a kód korábban két helyen élt: a sablonszűrőkben (`render.py`) és a
narratíva hivatkozásaiban (`narrative.py`). A kettő elcsúszott: a narratíva
mindig magyarul formázott, így az angol riport vezetői összefoglalójában
`33,2×`, `91,7%` és „2026. július” állt, két sorral lejjebb pedig a sablon
`33.2×`-e. Egy riporton belül kétféle jelölés elírásnak látszik.

Magyarul az ezres tagolás nem törhető szóköz: a szám nem törhet két sorba.
"""

from pipeline import i18n
from pipeline.labels import currency_label, money_digits

# A szimbólumos pénznemek angolul a szám elé kerülnek; a betűkódok (EUR,
# HUF → Ft) mindkét nyelven mögé.
SYMBOLS = {"USD": "$", "GBP": "£"}


def number(value, digits: int = 0, language: str = "hu") -> str:
    """Magyar: nem törhető szóköz ezres, vessző tizedes. Angol: vessző és pont."""
    if value is None:
        return "–"
    text = f"{float(value):,.{digits}f}"
    if language != "hu":
        return text
    return text.replace(",", " ").replace(".", ",")


def signed(value, digits: int = 0, language: str = "hu") -> str:
    """Előjeles változás: `+412` vagy `−87`.

    A mínusz valódi mínuszjel (U+2212), nem kötőjel — a kötőjel a számjegyek
    mellett elvész, és egy csökkenés úgy néz ki, mintha növekedés volna.
    """
    if value is None:
        return "–"
    text = number(abs(value), digits, language)
    return f"+{text}" if value > 0 else (f"−{text}" if value < 0 else text)


def money(value, currency: str, language: str = "hu") -> str:
    amount = number(value, money_digits(currency), language)
    if language != "hu" and currency in SYMBOLS:
        return f"{SYMBOLS[currency]}{amount}"
    return f"{amount} {currency_label(currency)}"


def percent(share, digits: int = 1, language: str = "hu") -> str:
    """Arányból százalék: `0.917` → `91,7%`."""
    return f"{number(float(share) * 100, digits, language)}%"


def multiplier(value, language: str = "hu") -> str:
    return f"{number(value, 1, language)}×"


def month(period: str, language: str = "hu") -> str:
    """`2026-07` → `2026. július` / `July 2026`."""
    year, month_number = str(period).split("-")[:2]
    name = i18n.months(language)[int(month_number) - 1]
    return f"{year}. {name}" if language == "hu" else f"{name} {year}"
