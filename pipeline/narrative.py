"""A narratíva-réteg: szöveg, amiben számot nem lehet leírni.

Ez az egyetlen pont, ahol nyelvi modell szöveget ír a riportba, tehát itt a
legnagyobb a kockázat, hogy egy tetszetős, de hamis szám kikerül az ügyfélhez.
A védelem nem utólagos ellenőrzés, hanem a lehetőség elvétele: a szövegben
**minden számjegy tiltott**, számra csak `{mezo.ut|formazo}` alakban lehet
hivatkozni.

Magyarul ez nem kényelmetlen: „a hat legjobb poszt" kiírva természetesebb is.
Ahol tényleg szám kell, ott adat van mögötte — tehát van mire hivatkozni.
"""

import re

from pipeline.errors import NarrativeError

REFERENCE = re.compile(r"\{([a-z_]+(?:\.[a-z_]+)*)(?:\|([a-z]+))?\}")
DIGIT = re.compile(r"\d")

MONTHS_HU = [
    "január", "február", "március", "április", "május", "június",
    "július", "augusztus", "szeptember", "október", "november", "december",
]

# A blokkok, amiket Claude ír. A `guidance` a SKILL.md-be és a
# narrative-guide.md-be kerül — a séma írja le önmagát.
BLOCKS = {
    "executive_summary": {
        "label": "Vezetői összefoglaló",
        "guidance": (
            "Három-négy mondat arról, mi történt a hónapban és miért. "
            "A legfontosabb állítással kezdj, ne a felsorolással."
        ),
    },
    "key_finding": {
        "label": "A hónap kulcsmegállapítása",
        "guidance": (
            "Egyetlen megállapítás, ami a döntést befolyásolja. "
            "`title` rövid állítás, `body` két-három mondat indoklás."
        ),
    },
    "what_worked": {
        "label": "Mi működött",
        "guidance": "Két-három pont, mindegyik konkrét tartalomra vagy kampányra mutat.",
    },
    "what_to_improve": {
        "label": "Min javítsunk",
        "guidance": (
            "Két-három pont. Ne hibáztass — azt írd le, mit csinálunk másképp."
        ),
    },
    "next_steps": {
        "label": "Következő lépések",
        "guidance": "Három-négy lépés, fontossági sorrendben, mindegyik cselekvés.",
    },
}


def _number(value, digits: int = 0) -> str:
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def _lookup(path: str, data: dict):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise NarrativeError(f"nincs ilyen mező: {path!r}")
        current = current[part]
    return current


def _format(value, formatter: str | None, data: dict) -> str:
    if formatter in (None, "num"):
        return _number(value)
    if formatter == "money":
        return f"{_number(value, 2)} {data['paid']['currency']}"
    if formatter == "pct":
        return f"{_number(float(value) * 100, 1)}%"
    if formatter == "x":
        return f"{_number(value, 1)}×"
    if formatter == "month":
        year, month = str(value).split("-")
        return f"{year}. {MONTHS_HU[int(month) - 1]}"
    if formatter == "raw":
        return str(value)
    raise NarrativeError(f"ismeretlen formázó: {formatter!r}")


def resolve(text: str, data: dict) -> str:
    """Behelyettesítés — de előbb a számjegy-tilalom."""
    without_refs = REFERENCE.sub("", text)
    if DIGIT.search(without_refs):
        found = "".join(DIGIT.findall(without_refs))
        raise NarrativeError(
            f"leírt szám a narratívában ({found!r}): {text[:80]!r}. "
            "Számot nem lehet beírni, csak hivatkozni rá: {mezo.ut|formazo}."
        )

    def replace(match: re.Match) -> str:
        return _format(_lookup(match.group(1), data), match.group(2), data)

    return REFERENCE.sub(replace, text)


def resolve_all(narrative, data: dict):
    """Rekurzívan végigmegy a narratíva teljes szerkezetén."""
    if isinstance(narrative, str):
        return resolve(narrative, data)
    if isinstance(narrative, list):
        return [resolve_all(item, data) for item in narrative]
    if isinstance(narrative, dict):
        return {key: resolve_all(value, data) for key, value in narrative.items()}
    return narrative
