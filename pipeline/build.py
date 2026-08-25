import json
from calendar import monthrange
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path

import yaml

from pipeline import bootstrap, compare, followers, guards, kpi, manual
from pipeline import performance as performance_mod
from pipeline.detect import scan
from pipeline.errors import (
    DuplicateSourceError,
    MissingConfigError,
    NarrativeError,
    UnmatchedBoostError,
    WrongFormatError,
    NoSourceError,
    UnknownSourceError,
)
from pipeline.join import join_posts
from pipeline.parsers import meta_ads, meta_content, meta_daily, zoomsphere


# Ezekből pontosan egy tartozik egy hónaphoz. A `meta_daily` szándékosan nincs
# itt: abból metrikánként jön egy. A `meta_content` sem — abból **csatornánként**
# egy, ezért azt a csatorna ismeretében külön kell őrizni (lásd lentebb).
SINGLETON_SOURCES = {
    "zoomsphere": "ZoomSphere export",
    "meta_ads": "Meta Ads export",
}

# Nem a várt formátum, de a tartalma jó lehet. A menedzser véletlenül PDF-et
# vagy régi Excelt tölt le — ilyenkor nem az a válasz, hogy „ismeretlen fájl",
# hanem az, hogy mit lehet vele kezdeni.
CONVERTIBLE = {
    "spreadsheet": "XLSX, de nem ZoomSphere-export. Ha ez a Meta Ads-export, "
    "mentsd CSV-ként (vagy szólj, és átalakítom) — a tartalma jó.",
    "pdf": "PDF. Két eset van, és mást kell tenni velük:\n"
    "      · ZoomSphere-export → töltsd le újra XLSX-ként. A PDF elvileg sem "
    "elég: nincs benne poszt-azonosító és kép-URL.\n"
    "      · korábbi havi riport → NEM az input mappába való. Tedd a hónap "
    "mappájába, és futtasd rá:\n"
    "          python tools/import_previous.py <fájl>\n"
    "        Ez javaslatot ír ki, nem previous.json-t — a számokat neked kell "
    "jóváhagynod. Vigyázz: a kézzel készült riportok időszaka gyakran nem "
    "naptári hónap, és akkor a belőlük számolt változás nem változás.",
    "legacy_office": "régi Office-formátum (.xls/.doc). Mentsd el XLSX-ként "
    "vagy CSV-ként, vagy szólj, és átalakítom.",
    "office": "Word- vagy más Office-dokumentum, nem táblázat-export.",
}


def _serialise(value):
    if is_dataclass(value):
        return {key: _serialise(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialise(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def load_config(directory: Path) -> dict:
    """Az ügyfél beállításai. Új ügyfélnél ez még nincs meg — a hibaüzenet
    ezért a kitöltött sablont adja vissza, nem csak a hiány tényét. Amit az
    exportokból ki lehet olvasni, azt ki is olvassuk: az oldalazonosítót
    bekérni olyasmi, amit már megkaptunk."""
    path = Path(directory) / "client.yaml"
    if not path.exists():
        found = bootstrap.suggest(Path(directory) / "input")
        lead = (
            "Az exportokból kitöltöttem, amit lehetett — a <…> részeket egészítsd ki:"
            if found
            else "Hozd létre ezzel a tartalommal, kitöltve:"
        )
        raise MissingConfigError(
            f"nincs client.yaml itt: {path.parent}\n{lead}\n\n"
            f"{bootstrap.template(found)}"
        )
    # A követőszámot itt még nem ellenőrizzük: lehet, hogy nem is kell megadni,
    # mert az előző hónapból továbbszámolható. Ahhoz viszont a napi adat kell,
    # ami csak a források beolvasása után áll elő. Lásd `followers.resolve`.
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# Mi hiányozhat, és mibe kerül. A varázsló ebből dolgozik: nem elég tudni,
# hogy nincs meg — azt is meg kell mondani, mi vész el nélküle.
EXPECTED = {
    "zoomsphere": "ZoomSphere tartalomnaptár — enélkül nincs kreatív és nincs poszt-szöveg",
    "meta_ads": "Meta Ads export — enélkül nincs költés és nincs boost-adat",
}
EXPECTED_PER_CHANNEL = {
    "content": "{channel} Tartalom export — enélkül nincs poszt-szintű elérés",
    "daily": "{channel} Eredmények napi CSV-k — enélkül nincs trendgörbe és nincs oldal-összesítés",
}


def _missing(seen: dict, content_channels: dict, daily_channels: set, client: dict):
    """A hiányzó források, emberi megfogalmazásban."""
    gaps = [text for kind, text in EXPECTED.items() if kind not in seen]

    channels = {}
    if client.get("fb_page_id") or client.get("fb_page_name"):
        channels["facebook"] = "Facebook"
    if client.get("ig_handle"):
        channels["instagram"] = "Instagram"

    for channel, label in channels.items():
        if channel not in content_channels:
            gaps.append(EXPECTED_PER_CHANNEL["content"].format(channel=label))
        if channel not in daily_channels:
            gaps.append(EXPECTED_PER_CHANNEL["daily"].format(channel=label))
    return gaps


# E fölött az arány fölött az illesztetlenség már nem lábjegyzet, hanem hiba.
UNMATCHED_BOOST_LIMIT = 0.5

# Ennyi nap eltérés a források záródátuma között még nem gyanús: egy csempe
# aznap még nem frissült. Ennél több már azt jelenti, hogy a letöltések nem
# ugyanakkor készültek.
COVERAGE_SPREAD_LIMIT = 2


AGENCY_DOMAIN = "helloagency.hu"


def _contact(directory: Path, config: dict) -> dict:
    """A záróoldal e-mail címe.

    Ügyfelenként külön postafiók van (`larus@`, `mammut@`), és a mappanévből
    jó eséllyel kitalálható. „Jó eséllyel" viszont nem elég egy olyan címhez,
    ami az ügyfélhez kimegy — ezért megjelöljük, hogy találgattuk, és a
    `--validate` emlékeztet, hogy nézze át.
    """
    client = config.get("client") or {}
    given = (client.get("contact_email") or "").strip()
    if given:
        return {"contact_email": given, "contact_email_is_guess": False}

    # `clients/larus/2026-07` → `larus`
    slug = Path(directory).resolve().parent.name.lower()
    slug = "".join(ch for ch in slug if ch.isalnum() or ch in "-_") or "agency"
    return {"contact_email": f"{slug}@{AGENCY_DOMAIN}", "contact_email_is_guess": True}


def _coverage(per_source: dict, period: str) -> dict:
    """A riport tényleges időszaka — a forrásfájlokból mérve.

    A menedzser nem mindig a hónap utolsó napján tölt le, és a Business Suite
    csempéi külön-külön zárulnak. A Mammut korábbi, kézi riportjaiban emiatt
    metrikánként hét-tíz nappal eltérő záródátumok keveredtek egyetlen
    dokumentumban — és ez sehol nem látszott.

    Ha a riport a naptári hónapot állítja, miközben az adat huszonnegyedikéig
    tart, akkor a következő havi összehasonlítás torz lesz, és senki nem tudja
    meg, miért. Ezért kimérjük, és kiírjuk.
    """
    year, month = (int(part) for part in period.split("-"))
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    # Csak a napi csempékből mérünk. Azokban egy sor egy mért nap, tehát a
    # legutolsó sor megmondja, meddig tart a mérés. A Tartalom- és az
    # Ads-export ezzel szemben DEKLARÁLT időszakot ad (a jelentés kezdete és
    # vége), ami akkor is a teljes hónap, ha az adat rövidebb — abból nem
    # derülne ki, hogy a menedzser huszonnegyedikén töltött le.
    daily = {
        name: window
        for name, (kind, window) in per_source.items()
        if kind == "meta_daily" and window and window[1]
    }
    if not daily:
        return {"coverage_start": first.isoformat(), "coverage_end": last.isoformat(),
                "coverage_partial": False, "coverage_spread": []}

    start = min(window[0] for window in daily.values())
    end = max(window[1] for window in daily.values())

    # Ha az egyes csempék más napon zárulnak, az pont az a hiba, amit a
    # korábbi kézi riportokban találtunk: egy dokumentumban keverednek a
    # különböző napokon lekérdezett állapotok.
    spread = sorted(
        (name, window[1].isoformat())
        for name, window in daily.items()
        if (end - window[1]).days > COVERAGE_SPREAD_LIMIT
    )

    return {
        "coverage_start": max(start, first).isoformat(),
        "coverage_end": min(end, last).isoformat(),
        "coverage_partial": end < last,
        "coverage_spread": [{"file": name, "end": value} for name, value in spread],
    }


def _check_boost_matching(joined, campaigns: list) -> None:
    """A boost-illesztés aránya nem lábjegyzet, hanem adathitelességi kérdés.

    A Mammut-próbán MINDEN boost illesztetlen maradt (egy elrontott előtag-regex
    miatt), és a build ettől még „sikeresen" lefutott. Pedig a riport két
    központi száma — a boost-szorzó és az organikus átlagelérés — pontosan erre az
    illesztésre épül: ha egy hirdetett poszt nem kapja meg a költését,
    organikusként számít bele az átlagba. A javítás után a szorzó 2,5×-ről
    4,7×-re változott. Mindkét szám hihető volt; az egyik hamis.

    Egy-két illesztetlen boost normális (a poszt korábbi hónapban jelent meg).
    A többség viszont azt jelenti, hogy a párosítás elromlott.
    """
    boosts = [c for c in campaigns if getattr(c, "is_boost", False)]
    if not boosts:
        return
    ratio = len(joined.unmatched_boosts) / len(boosts)
    if ratio <= UNMATCHED_BOOST_LIMIT:
        return

    names = "\n".join(f"  · {c.name}" for c in joined.unmatched_boosts[:6])
    more = len(joined.unmatched_boosts) - 6
    raise UnmatchedBoostError(
        f"a boostok {ratio:.0%}-a nem talált posztot "
        f"({len(joined.unmatched_boosts)} a {len(boosts)}-ból):\n{names}"
        + (f"\n  · …és még {more}" if more > 0 else "")
        + "\n\nEnnyi illesztetlenség mellett a boost-szorzó és az organikus "
        "átlagelérés is hamis lenne: a hirdetett posztok organikusként "
        "számítanának bele.\n"
        "Nézd meg: (1) a Tartalom exportok ugyanarra a hónapra szólnak-e, "
        "(2) mindkét csatornáról megvannak-e, (3) a kampánynevek tényleg a "
        "poszt szövegét tartalmazzák-e."
    )


def _obtainable(channels: dict, config: dict) -> list[dict]:
    """Amit a Meta nem exportál, de a felületén ott van, és még nincs megadva."""
    given = config.get("monthly_reach") or {}
    spec = manual.OBTAINABLE["monthly_reach"]

    return [
        {
            "key": f"monthly_reach.{name}",
            "label": f"{name} {spec['label']}",
            # Csatornánként más csempéből jön, és a nevük nem egyezik. Egyetlen
            # közös útmutató a rossz csempéhez küldené a menedzsert.
            "hint": spec["hint"][name],
            "why": spec["why"],
        }
        for name in sorted(channels)
        if not isinstance(given.get(name), int)
        if name in spec["hint"]
    ]


def load_narrative(directory: Path) -> dict | None:
    path = Path(directory) / "narrative.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        # A narratívát kézzel is szerkesztik, és a magyar idézőjel könnyen
        # egyenessel záródik — az pedig lezárja a JSON-stringet. A nyers
        # traceback ilyenkor semmit nem mond arról, mit kell javítani.
        raise NarrativeError(
            f"{path} nem érvényes JSON: {error.msg} "
            f"({error.lineno}. sor, {error.colno}. karakter).\n"
            "Gyakori ok: magyar idézőjelet nyitottál („), de egyenessel zártad "
            '(") — az lezárja a szöveget. A helyes záró: ”'
        ) from error


def build(directory: Path, period: str) -> dict:
    directory = Path(directory)
    config = load_config(directory)
    client = config["client"]
    overrides = config.get("daily_metric_overrides") or {}
    overrides = {key: tuple(value) for key, value in overrides.items()}

    items, content, campaigns, series = [], [], [], []
    ads_payload = None
    hints: dict[str, str] = {}
    unknown: list[str] = []
    screenshots: list[str] = []
    wrong_format: list[tuple[str, str]] = []
    coverage: dict[str, tuple] = {}
    # „Így értelmeztem a mappát" — a Mammut-próba hét csúszástípusából négy
    # teljesen néma volt: a rendszer nem hibázott, csak rosszul párosított.
    # A hiány jelentése nem elég; a saját értelmezésünket is jelentenünk kell.
    inventory: list[tuple[str, str, str]] = []
    seen: dict[str, str] = {}
    content_channels: dict[str, str] = {}

    for source in scan(directory / "input"):
        if source.kind in SINGLETON_SOURCES:
            if source.kind in seen:
                raise DuplicateSourceError(
                    f"két {SINGLETON_SOURCES[source.kind]} van a mappában: "
                    f"{seen[source.kind]} és {source.path.name}. "
                    "Töröld a régit — különben csendben az egyikük adata veszne el."
                )
            seen[source.kind] = source.path.name

        if source.kind == "zoomsphere":
            parsed = zoomsphere.parse(source.path)
            items = parsed.payload
            inventory.append(
                (source.path.name, "ZoomSphere", f"{len(parsed.payload)} elem")
            )
        elif source.kind == "meta_ads":
            parsed = meta_ads.parse(source.path)
            ads_payload = parsed.payload
            campaigns = parsed.payload.campaigns
            boosts = sum(1 for c in campaigns if c.is_boost)
            inventory.append(
                (
                    source.path.name,
                    "Meta Ads",
                    f"{len(campaigns)} kampány ({boosts} boost), "
                    f"{parsed.payload.currency}",
                )
            )
        elif source.kind == "meta_content":
            parsed = meta_content.parse(source.path)
            by_channel = Counter(post.channel for post in parsed.payload)
            empty = sum(1 for post in parsed.payload if not post.caption.strip())
            inventory.append(
                (
                    source.path.name,
                    "Tartalom",
                    ", ".join(f"{n} {c}" for c, n in sorted(by_channel.items()))
                    # Az üres poszt-szöveg NÉMA hiba: nem áll meg tőle semmi,
                    # csak a boost-illesztés hiúsul meg, mert az szöveg alapján
                    # megy. A Mammutnál minden IG-poszt így jött be.
                    + (f" · ⚠ {empty} szöveg nélkül" if empty else ""),
                )
            )
            # Tartalom exportból csatornánként egy van. Kettő ugyanarra a
            # csatornára minden posztot megkétszerezne — az elérés-összegek és
            # az átlagok csendben elromlanának.
            for channel in {post.channel for post in parsed.payload}:
                if channel in content_channels:
                    raise DuplicateSourceError(
                        f"két {channel} Tartalom export van a mappában: "
                        f"{content_channels[channel]} és {source.path.name}. "
                        "Töröld a régit — különben minden poszt kétszer szerepelne."
                    )
                content_channels[channel] = source.path.name
            content += parsed.payload
        elif source.kind == "meta_daily":
            parsed = meta_daily.parse(source.path, overrides=overrides)
            series.append(parsed.payload)
            # A csatorna és az összeg együtt: ha két azonos nevű csempe
            # ugyanarra a csatornára került, az itt szemmel látszik. Ez volt a
            # Mammut egyik néma hibája — a két „Megtekintések" felcserélése.
            inventory.append(
                (
                    source.path.name,
                    f"{parsed.payload.channel} / {parsed.payload.field}",
                    f"összeg {sum(v for _, v in parsed.payload.points):,}".replace(
                        ",", " "
                    ),
                )
            )
        elif source.kind == "screenshot":
            # A menedzser gyakran bedobja a Business Suite képernyőképeit is.
            # Ez nem szemét: ezekről olvasható le a havi elérés és a változás.
            # Nem szabad hibának venni, és nem szabad megkérdezni tőle olyat,
            # ami ezeken ott van.
            screenshots.append(source.path.name)
            continue
        elif source.kind == "ignored_duplicate":
            inventory.append(
                (
                    source.path.name,
                    "Kihagyott hibás duplikátum",
                    "egy azonos nevű, felismerhető exportot használunk helyette",
                )
            )
            continue
        elif source.kind in CONVERTIBLE:
            wrong_format.append((source.path.name, CONVERTIBLE[source.kind]))
            continue
        else:
            unknown.append(source.path.name)
            continue

        guards.check_period(source.kind, parsed.period, period)
        # Meddig ér az adat? A menedzser nem mindig a hónap utolsó napján tölt
        # le, és a Business Suite csempéi külön-külön zárulnak. Ha ezt nem
        # mérjük ki, a riport a teljes hónapot állítja — és a következő
        # hónaphoz képest torz lesz az összehasonlítás, magyarázat nélkül.
        coverage[source.path.name] = (source.kind, parsed.period)
        hints.update({k: v for k, v in parsed.client_hints.items() if v})

    if wrong_format:
        lines = "\n".join(f"  · {name} — {what}" for name, what in wrong_format)
        raise WrongFormatError(
            "nem a várt formátumban van néhány fájl:\n" + lines + "\n\n"
            "Ezeket nem tudom közvetlenül beolvasni. Két út van: töltsd le újra "
            "a helyes formátumban (ez a biztosabb), vagy szólj, és átalakítom — "
            "a PDF-ből és a régi Excelből ki tudom nyerni a táblázatot."
        )

    if unknown:
        raise UnknownSourceError(
            "nem azonosítható fájl az input mappában: "
            + ", ".join(unknown)
            + ".\nHa nem a riporthoz tartozik, vedd ki a mappából. Ha igen, akkor "
            "nem a Meta vagy a ZoomSphere exportja, vagy megszerkesztették — "
            "töltsd le újra, változtatás nélkül.\n"
            "Csendben átugrani nem tudjuk: ha mégis riportadat volt, egy egész "
            "csatorna hiányozna a riportból anélkül, hogy bárki észrevenné."
        )

    if not any([items, content, campaigns, series]):
        raise NoSourceError(
            f"{directory / 'input'}: egyetlen felismerhető forrásfájl sincs. "
            "Enélkül csak nullákkal teli riport készülne."
        )

    guards.check_client(hints, client)

    joined = join_posts(content=content, items=items, campaigns=campaigns)
    _check_boost_matching(joined, campaigns)

    channels = kpi.channel_blocks(
        series=series, posts=joined.posts, campaigns=campaigns
    )
    channels = _serialise(channels)
    # A pontozás a szerializált posztokon fut: szótárakkal dolgozik, és a
    # `score` blokk is oda kerül vissza. Elérés szerint rangsorolni annyi volna,
    # mint költés szerint — lásd `performance.py`.
    performance = {}
    for name, block in channels.items():
        performance[name] = performance_mod.findings(
            performance_mod.score_posts(block["posts"])
        )
    previous = compare.load_previous(directory)
    manual_values = manual.load_manual(directory)
    follower_counts, follower_origin = followers.resolve(
        config, channels, previous, period
    )

    return _serialise(
        {
            "meta": {
                "client": client["name"],
                "period": period,
                "currency": ads_payload.currency if ads_payload else "EUR",
                "language": config.get("report", {}).get("language", "hu"),
                # Mi legyen a nagy szám az összehasonlító oldalakon: a hónap
                # végeredménye (`value`) vagy a változás mértéke (`change`).
                # Kampányriportnál a második erősebb. A menedzser ezt
                # megjegyzésben szokta kérni, ezért kapcsoló, nem sablonátírás.
                "comparison_headline": config.get("report", {}).get(
                    "comparison_headline", "value"
                ),
                # Ügyfelenként külön postafiók van (larus@, mammut@…). A
                # mappanévből kitalált cím jó kiindulás, de nem biztos, hogy
                # helyes — ezért jelöljük, hogy találgatás, és a `--validate`
                # emlékeztet rá. Rossz e-mail a záróoldalon az ügyfélhez megy ki.
                **_contact(directory, config),
                # Meddig ér ténylegesen az adat — a fájlokból mérve, nem a
                # naptárból feltételezve.
                **_coverage(coverage, period),
            },
            "content": kpi.content_summary(items),
            # A posztok egyetlen helyen élnek: a csatorna-blokkokban. Lapos
            # másolatot nem tartunk mellette — két forrás ugyanarra elcsúszik.
            "channels": channels,
            # Melyik poszt teljesített jól — nem elérés, hanem rezonancia
            # szerint. A narratíva ebből tud állítást tenni.
            "performance": performance,
            # Az előző időszak jöhet a múlt havi report_data.json-ból
            # (`previous.json`), vagy — az első hónapban — a menedzser kézi
            # beviteléből. Ha egyik sincs, a blokk üres, és a riport
            # kitölthető mezőket mutat helyette.
            "comparison": {
                name: compare.deltas(
                    block["totals"],
                    (previous or {}).get("channels", {}).get(name, {}).get("totals")
                    or compare.previous_from_manual(
                        manual_values, name, block["totals"]
                    ),
                )
                for name, block in channels.items()
            },
            # A követőszám nem díszlet: belőle jön a növekedési ütem, és — ha a
            # menedzser beírja a havi elérést — az elérés/követő arány is.
            "audience": kpi.audience(
                channels, follower_counts, config.get("monthly_reach") or {}
            ),
            # Honnan tudjuk a követőszámot. A továbbszámolt értéket a
            # menedzsernek látnia kell, hogy ránézésre kiszúrja, ha elcsúszott.
            "follower_origin": follower_origin,
            "paid": kpi.paid_totals(campaigns),
            # Illeszkedik-e az előző havi adat a mostanihoz? Rés, átfedés vagy
            # ismeretlen időszak esetén a „változás" nem változás.
            "comparison_health": compare.coverage_check(
                previous, _coverage(coverage, period)
            ),
            "cross": kpi.cross_channel(joined.posts),
            "quality": {
                "posts_with_creative": sum(1 for p in joined.posts if p.creatives),
                # Amelyik posztnak nincs kreatívja, az a riportban helyőrzővel
                # jelenik meg. Ez majdnem mindig azt jelenti, hogy a poszt nem a
                # ZoomSphere-en keresztül ment ki, hanem közvetlenül a
                # felületen — a Meta tudja a számait, a ZoomSphere nem tud róla.
                # Enélkül a menedzser csak a kész riportban látja meg a lyukat.
                "posts_without_creative": [
                    (p.caption or p.post_id)[:60]
                    for p in joined.posts
                    if not p.creatives and p.organic_measured
                ],
                "posts_total": len(joined.posts),
                "posts_measured": sum(1 for p in joined.posts if p.organic_measured),
                # Hány poszt kapta meg a költését. Ha ez nulla, miközben van
                # boost, a párosítás elromlott — és a boost-szorzó hamis.
                "posts_with_spend": sum(1 for p in joined.posts if p.paid),
                "unmatched_boosts": [c.name for c in joined.unmatched_boosts],
                # Valódi költés, ami ma teljesen kimarad a riportból: a poszt
                # egy korábbi hónapban jelent meg, a hirdetés viszont most
                # futott rá. Ez NEM hiba — a `--validate` mégis ugyanúgy
                # figyelmezteti, mint egy valódi elakadást.
                "earlier_posts_boosted_now": [
                    {
                        "name": c.name,
                        "spend": c.spend,
                        "reach": c.reach,
                        "channel": c.channel,
                    }
                    for c in joined.unmatched_boosts
                ],
                "unmatched_content": [p.post_id for p in joined.unmatched_content],
                "dropped_zero_campaign_rows": (
                    ads_payload.dropped_zero_rows if ads_payload else 0
                ),
            },
            "manual": manual_values,
            # Ami nincs exportban, de a felületről leolvasható. Nem hiba, és nem
            # is az ügyfélre tartozik — a menedzsernek szól, hogy tudjon róla.
            "obtainable": _obtainable(channels, config),
            # A menedzser feltöltött képernyőképeket is. Ezekről a hiányzó
            # számok jó eséllyel leolvashatók — ilyenkor nem kérdezünk, hanem
            # megnézzük.
            "screenshots": screenshots,
            "inventory": [
                {"file": name, "as": what, "detail": detail}
                for name, what, detail in sorted(inventory)
            ],
            "missing": _missing(
                seen,
                content_channels,
                {entry.channel for entry in series},
                client,
            ),
        }
    )
