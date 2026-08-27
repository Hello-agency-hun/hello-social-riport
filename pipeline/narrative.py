"""A narratíva-réteg: szöveg, amiben számot nem lehet leírni.

Ez az egyetlen pont, ahol nyelvi modell szöveget ír a riportba, tehát itt a
legnagyobb a kockázat, hogy egy tetszetős, de hamis szám kikerül az ügyfélhez.
A védelem nem utólagos ellenőrzés, hanem a lehetőség elvétele: a szövegben
**minden számjegy tiltott**, számra csak `{mezo.ut|formazo}` alakban lehet
hivatkozni.

Magyarul ez nem kényelmetlen: „a hat legjobb poszt" kiírva természetesebb is.
Ahol tényleg szám kell, ott adat van mögötte — tehát van mire hivatkozni.
"""

import html
import re

from pipeline.labels import currency_label, money_digits

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

# Nem minden riportban kell külön kampányállapot-értelmezés. Ha van Meta Ads
# export, ez a két szöveges levél megjelenhet és ugyanúgy szerkeszthető, mint a
# kötelező narratívablokkok; a kampányok exportált adatai nem kerülnek ide.
OPTIONAL_BLOCKS = {
    "campaign_status": {
        "label": "Kampányállapotok értelmezése",
        "guidance": (
            "A `title` röviden foglalja össze a kampánymezőnyt, a `body` pedig "
            "magyarázza el az állapotokat és az Ads-lekérési ablak pontosságát. "
            "Exportált dátumot, eredményt vagy státuszt ne másolj ide kézzel."
        ),
    }
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
        currency = data["paid"]["currency"]
        return f"{_number(value, money_digits(currency))} {currency_label(currency)}"
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


def _check_digits(text: str) -> None:
    without_refs = REFERENCE.sub("", text)
    if DIGIT.search(without_refs):
        found = "".join(DIGIT.findall(without_refs))
        raise NarrativeError(
            f"leírt szám a narratívában ({found!r}): {text[:80]!r}. "
            "Számot nem lehet beírni, csak hivatkozni rá: {mezo.ut|formazo}."
        )


def _escape(text: str) -> str:
    """Escape-elt szöveg, a sortörésekből `<br>`.

    A `<p>`-be tett nyers sortörést a böngésző szóközzé olvasztja, tehát a
    menedzser Enterei nyomtalanul eltűnnének a mentés után. A csere az
    escape UTÁN történik: a `<br>` az egyetlen jel, amit beengedünk.
    """
    return html.escape(text).replace(chr(10), "<br>")


def resolve(text: str, data: dict) -> str:
    """Behelyettesítés — de előbb a számjegy-tilalom."""
    _check_digits(text)

    def replace(match: re.Match) -> str:
        return _format(_lookup(match.group(1), data), match.group(2), data)

    return REFERENCE.sub(replace, text)


def resolve_markup(text: str, data: dict) -> str:
    """Mint a `resolve`, de a behelyettesített értékek szerkeszthetetlen
    szigetek, amik magukban hordozzák a hivatkozásukat.

    A menedzser a böngészőben a **megjelenített** szöveget látja. Ha azt
    mentenénk vissza sablonként, a hivatkozások helyére beírt számok kerülnének
    — és a következő build a saját narratíváját utasítaná el a számjegy-tilalom
    miatt. Egyetlen szerkesztés tönkretenné a riportot.

    Ezért minden érték `<span data-ref="{...}" contenteditable="false">`-be
    kerül: a szöveg körülötte szabadon átírható, a szám viszont sem elgépelni,
    sem a hivatkozását elveszíteni nem lehet. A `review.js` ebből állítja
    vissza az eredeti sablont.
    """
    _check_digits(text)

    parts: list[str] = []
    position = 0
    for match in REFERENCE.finditer(text):
        parts.append(_escape(text[position : match.start()]))
        value = _format(_lookup(match.group(1), data), match.group(2), data)
        parts.append(
            f'<span class="val" contenteditable="false" '
            f'data-ref="{html.escape(match.group(0), quote=True)}">'
            f"{html.escape(value)}</span>"
        )
        position = match.end()
    parts.append(_escape(text[position:]))
    return "".join(parts)


# A magyar ábécé sajátjai. Az `ő` és az `ű` gyakorlatilag csak magyarban
# fordul elő latin írásban; a többi is erős jel együtt.
HUNGARIAN_LETTERS = re.compile(r"[őűáéíóöúüŐŰÁÉÍÓÖÚÜ]")


def check_language(narrative, language: str) -> None:
    """A narratíva a riport nyelvén készüljön.

    Ha a riport angol, de a narratíva magyarul íródott, a build ma zokszó
    nélkül lefutna, és az ügyfél kapna egy angol keretbe ágyazott magyar
    elemzést. Ez nem apró szépséghiba: pont a riport legfontosabb oldalai
    lennének olvashatatlanok annak, akinek szól.

    A nyelvet a `client.yaml` `report.language` mezője dönti el, nem az, hogy
    az agent épp milyen nyelven beszélget a menedzserrel.
    """
    if language == "hu":
        return

    texts = []

    def collect(node):
        if isinstance(node, str):
            texts.append(node)
        elif isinstance(node, list):
            for item in node:
                collect(item)
        elif isinstance(node, dict):
            for value in node.values():
                collect(value)

    collect(narrative)
    joined = " ".join(texts)
    hits = HUNGARIAN_LETTERS.findall(joined)
    # Néhány ékezet lehet idézett poszt-szöveg vagy márkanév; a tömeges
    # előfordulás viszont azt jelenti, hogy az egész magyarul íródott.
    if len(hits) > 12:
        raise NarrativeError(
            f"a riport nyelve `{language}`, de a narratíva magyarul íródott "
            f"({len(hits)} magyar ékezetes betű).\n"
            "A vezetői összefoglalót, a kulcsmegállapítást és a listákat a "
            "riport nyelvén kell megírni — az ügyfél ezeket olvassa.\n"
            "A nyelvet a client.yaml `report.language` mezője dönti el."
        )


def resolve_all(narrative, data: dict, markup: bool = False):
    """Rekurzívan végigmegy a narratíva teljes szerkezetén."""
    if isinstance(narrative, str):
        return resolve_markup(narrative, data) if markup else resolve(narrative, data)
    if isinstance(narrative, list):
        return [resolve_all(item, data, markup) for item in narrative]
    if isinstance(narrative, dict):
        return {
            key: resolve_all(value, data, markup) for key, value in narrative.items()
        }
    return narrative
