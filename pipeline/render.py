"""A riport összeállítása. Csak a `report_data.json`-t olvassa, forrásfájlt soha."""

import json
from datetime import date
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import charts, i18n, images, labels
from pipeline import manual as manual_module
from pipeline import performance
from pipeline import narrative as narrative_module
from pipeline.assets import TEMPLATES, logo, stylesheet

MONTHS_HU = [
    "január", "február", "március", "április", "május", "június",
    "július", "augusztus", "szeptember", "október", "november", "december",
]


def _number(value, digits: int = 0, language: str = "hu") -> str:
    """Magyar: szóköz ezres, vessző tizedes. Angol: vessző ezres, pont tizedes.

    Egyetlen riporton belül nem keveredhet a kettő: magyar szövegben egy
    angolosan tördelt szám elírásnak látszik, és fordítva.
    """
    if value is None:
        return "–"
    text = f"{float(value):,.{digits}f}"
    if language != "hu":
        return text
    return text.replace(",", " ").replace(".", ",")


def _signed(value, digits: int = 0, language: str = "hu") -> str:
    """Előjeles változás: `+412` vagy `−87`.

    A mínusz valódi mínuszjel (U+2212), nem kötőjel — a kötőjel a számjegyek
    mellett elvész, és egy csökkenés úgy néz ki, mintha növekedés volna.
    """
    if value is None:
        return "–"
    text = _number(abs(value), digits, language)
    return f"+{text}" if value > 0 else (f"−{text}" if value < 0 else text)


def _money(value, currency: str, language: str = "hu") -> str:
    """A pénznem helye nyelvfüggő: a szimbólumok (`$`, `£`) angolul a szám elé
    kerülnek, a betűkódok (HUF, EUR) mindkét nyelven mögé."""
    amount = _number(value, 2, language)
    symbols = {"USD": "$", "GBP": "£"}
    if language != "hu" and currency in symbols:
        return f"{symbols[currency]}{amount}"
    return f"{amount} {currency}"


def _period_name(period: str, language: str = "hu") -> str:
    year, month = period.split("-")
    name = i18n.months(language)[int(month) - 1]
    return f"{year}. {name}" if language == "hu" else f"{name} {year}"


def _period_range(period: str) -> str:
    """`2026-07` → `2026-07-01 – 2026-07-31`.

    A korábbi, kézzel készült riportok nem naptári hónapot fedtek: a készítő
    metrikánként más napon nyitotta meg a Business Suite csempéit, így egy
    dokumentumon belül keveredtek a hónap huszonegyedikei és harmincegyedikei
    állapotok. Az átálláskor az ügyfél ezért ugrást fog látni — a riportnak ki
    kell mondania, mit mért, különben a különbség megmagyarázhatatlan.
    """
    from calendar import monthrange

    year, month = (int(part) for part in period.split("-"))
    last = monthrange(year, month)[1]
    return f"{year}-{month:02d}-01 – {year}-{month:02d}-{last}"


def _measured_range(meta: dict) -> str:
    """A ténylegesen mért időszak, a forrásfájlokból.

    Nem a naptári hónapot írjuk ki, hanem ameddig az adat ér. A menedzser nem
    mindig a hónap utolsó napján tölt le; ha ilyenkor teljes hónapot
    állítanánk, a következő havi összehasonlítás csendben torz lenne.
    """
    start = meta.get("coverage_start")
    end = meta.get("coverage_end")
    if not start or not end:
        return _period_range(meta["period"])
    return f"{start} – {end}"


def _environment(language: str = "hu") -> Environment:
    """A nyelv a szűrőkbe van kötve, nem a hívási helyekre bízva.

    Ha minden `| num` hívásnál külön át kellene adni, egy elfelejtett helyen
    magyar formátumú szám maradna az angol riportban — és ez nem hibaüzenettel
    derülne ki, hanem az ügyfélnél.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = lambda v, d=0: _number(v, d, language)
    env.filters["money"] = lambda v, c: _money(v, c, language)
    env.filters["signed"] = lambda v, d=0: _signed(v, d, language)
    env.filters["field"] = lambda k: labels.page_field(k, language)
    env.filters["result"] = lambda k: labels.result_type(k, language)
    env.filters["channel"] = labels.channel
    env.filters["ptype"] = lambda k: labels.post_type(k, language)
    env.filters["short"] = labels.shorten
    return env


def _balanced_chunks(items: list, per_page: int = 3) -> list[list]:
    """Oldalankénti bontás árva kártya nélkül.

    Négy poszt `batch(3)`-mal 3+1-re esne szét, és a második lapon egyetlen
    kártya árválkodna. Kiegyenlítve 2+2 lesz belőle.
    """
    if not items:
        return []
    pages = -(-len(items) // per_page)
    size = -(-len(items) // pages)
    return [items[i : i + size] for i in range(0, len(items), size)]


def render(
    data: dict,
    cache_dir: Path,
    narrative: dict | None = None,
    fetcher: Callable[[str], bytes] = images.fetch,
    manual: dict | None = None,
) -> str:
    # A nyelv a riportadatból jön, az pedig a `client.yaml`-ből. Egy helyen
    # dől el, és onnantól a szűrők, a feliratok és a diagramok is ezt követik.
    language = data["meta"].get("language") or i18n.DEFAULT
    text = i18n.strings(language)

    if narrative:
        narrative_module.check_language(narrative, language)
    resolved = (
        narrative_module.resolve_all(narrative, data, markup=True)
        if narrative
        else None
    )

    organic = data["cross"]["organic_reach"]
    boosted = data["cross"]["boosted_reach"]

    # Egy oldalon négy görbe fut; ha mind zöld, összemosódnak. A ciklus a
    # márkapaletta hangosabb színeit is behozza, nem csak az akcentust.
    curve_colours = [
        "var(--accent)",
        "var(--brand-rose)",
        "var(--brand-blue)",
        "var(--brand-pink)",
    ]

    trends = {}
    for name, block in data.get("channels", {}).items():
        trends[name] = [
            (
                labels.page_field(field, language),
                charts.line_chart(
                    [
                        (date.fromisoformat(day), value)
                        for day, value in block["daily"][field]
                    ],
                    label=f"{labels.channel(name)} — {labels.page_field(field, language)}",
                    height=175,
                    colour=curve_colours[index % len(curve_colours)],
                    language=language,
                    total_label=text.total,
                ),
            )
            for index, field in enumerate(sorted(block["daily"]))
        ]

    channel_posts = {}
    ranking: dict[str, str] = {}
    for name, block in data.get("channels", {}).items():
        # Teljesítmény szerint, nem elérés szerint. Elérés szerint rangsorolni
        # annyi volna, mint költés szerint: amelyik posztra a legtöbb pénz ment,
        # az lenne elöl — ez tautológia, nem megállapítás. Lásd `performance.py`.
        ranked = performance.balanced(block["posts"], limit=6)
        if not ranked:
            # Nincs mért elérés ezen a csatornán — marad a régi sorrend, hogy
            # a boostolt posztok legalább megjelenjenek.
            ranked = sorted(block["posts"], key=lambda post: -post["reach"])
        selected = [post for post in ranked if post["reach"]][:6]
        if not selected:
            # Ezen a csatornán nincs mért elérés — a boostoltakat emeljük ki,
            # mert azokról van mért fizetett adatunk.
            selected = [post for post in ranked if post.get("paid")][:6]
        for post in selected:
            sources = post["creatives"][:1]
            # Ha a ZoomSphere nem tud a posztról (közvetlenül a felületen ment
            # ki), a kreatív hiányzik, de a Facebook `og:image`-e megvan.
            # Kiegészítés, nem forrás: ha nem jön össze, marad a helyőrző, és a
            # `--validate` akkor is felsorolja a posztot.
            if not sources and post.get("permalink"):
                fallback, why = images.creative_from_permalink(
                    post["permalink"], fetcher=fetcher
                )
                # Az indoklást akkor is eltesszük, ha sikerült: a menedzser
                # csak így tudja eldönteni, érdemes-e kézzel pótolni a képet.
                post["creative_recovery"] = why
                if fallback:
                    sources = [fallback]

            uris = images.embed(sources, cache_dir=cache_dir, fetcher=fetcher)
            post["thumb"] = uris[0] if uris else images.PLACEHOLDER
        channel_posts[name] = _balanced_chunks(selected)
        # Az elérés szerinti rangsor egy pillantással megmutatja a sorrendet,
        # amit a kártyák oldalanként háromra bontva nem tudnak.
        # A diagram azt mutatja, hányszorosa a poszt a csatorna szokásos
        # teljesítményének — nem az elérést, mert azt a költés dönti el.
        measured = [post for post in selected if post.get("score")]
        if measured:
            ranking[name] = charts.bar_chart(
                [
                    (
                        labels.shorten(post["caption"], 44) or "(nincs szöveg)",
                        post["score"]["vs_typical"] or 0,
                    )
                    for post in measured
                ],
                label=f"{labels.channel(name)} — {text.performance_vs_typical}",
                language=language,
                value_format=lambda value: _number(value, 1) + "×",
            )

    template = _environment(language).get_template("report.html.j2")
    return template.render(
        data=data,
        trends=trends,
        channel_posts=channel_posts,
        ranking=ranking,
        # A módszertani oldal egyszer szerepel, az első olyan csatorna előtt,
        # ahol egyáltalán van pontozott poszt. Vakon az első csatornához kötve
        # kimaradna, ha épp azon nincs mért elérés.
        methodology_channel=next(
            (
                name
                for name, chunks in channel_posts.items()
                if chunks and chunks[0] and chunks[0][0].get("score")
            ),
            None,
        ),
        narrative=resolved,
        css=stylesheet(),
        logo_lockup=logo("hello-lockup"),
        logo_mark=logo("hello-mark"),
        t=text,
        # A gombfeliratok a JavaScriptbe is átmennek: az a kód a sablonon kívül
        # él, és az angol próbán pont ezek maradtak magyarul.
        ui_labels=json.dumps(i18n.ui(language), ensure_ascii=False),
        period_name=_period_name(data["meta"]["period"], language),
        period_range=_measured_range(data["meta"]),
        coverage_partial=data["meta"].get("coverage_partial", False),
        generated=date.today().isoformat(),
        charts={
            "reach_split": charts.donut(
                [(text.boosted_posts_label, boosted), (text.organic_posts_label, organic)],
                label=text.reach_split_label,
                language=language,
            ),
        },
        currency=data["paid"]["currency"],
        manual=manual or {},
        manual_slots=manual_module.SLOTS,
        review_js=(TEMPLATES / "review.js").read_text(encoding="utf-8"),
    )
