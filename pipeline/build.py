import json
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
    "pdf": "PDF. Ha ez a ZoomSphere-export, töltsd le XLSX-ként; ha nem megy, "
    "ki tudom nyerni belőle a táblázatot.",
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
        elif source.kind == "meta_ads":
            parsed = meta_ads.parse(source.path)
            ads_payload = parsed.payload
            campaigns = parsed.payload.campaigns
        elif source.kind == "meta_content":
            parsed = meta_content.parse(source.path)
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
        elif source.kind == "screenshot":
            # A menedzser gyakran bedobja a Business Suite képernyőképeit is.
            # Ez nem szemét: ezekről olvasható le a havi elérés és a változás.
            # Nem szabad hibának venni, és nem szabad megkérdezni tőle olyat,
            # ami ezeken ott van.
            screenshots.append(source.path.name)
            continue
        elif source.kind in CONVERTIBLE:
            wrong_format.append((source.path.name, CONVERTIBLE[source.kind]))
            continue
        else:
            unknown.append(source.path.name)
            continue

        guards.check_period(source.kind, parsed.period, period)
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
                "unmatched_boosts": [c.name for c in joined.unmatched_boosts],
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
            "missing": _missing(
                seen,
                content_channels,
                {entry.channel for entry in series},
                client,
            ),
        }
    )
