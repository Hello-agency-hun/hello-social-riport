"""A riport összeállítása. Csak a `report_data.json`-t olvassa, forrásfájlt soha."""

from datetime import date
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import charts, images, labels
from pipeline import manual as manual_module
from pipeline import performance
from pipeline import narrative as narrative_module
from pipeline.assets import TEMPLATES, logo, stylesheet

MONTHS_HU = [
    "január", "február", "március", "április", "május", "június",
    "július", "augusztus", "szeptember", "október", "november", "december",
]


def _number(value, digits: int = 0) -> str:
    """Magyar formátum: szóköz ezres elválasztó, vessző tizedesjel."""
    if value is None:
        return "–"
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def _signed(value, digits: int = 0) -> str:
    """Előjeles változás: `+412` vagy `−87`.

    A mínusz valódi mínuszjel (U+2212), nem kötőjel — a kötőjel a számjegyek
    mellett elvész, és egy csökkenés úgy néz ki, mintha növekedés volna.
    """
    if value is None:
        return "–"
    text = _number(abs(value), digits)
    return f"+{text}" if value > 0 else (f"−{text}" if value < 0 else text)


def _money(value, currency: str) -> str:
    return f"{_number(value, 2)} {currency}"


def _period_hu(period: str) -> str:
    year, month = period.split("-")
    return f"{year}. {MONTHS_HU[int(month) - 1]}"


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = _number
    env.filters["money"] = _money
    env.filters["field"] = labels.page_field
    env.filters["result"] = labels.result_type
    env.filters["channel"] = labels.channel
    env.filters["ptype"] = labels.post_type
    env.filters["short"] = labels.shorten
    env.filters["signed"] = _signed
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
                labels.page_field(field),
                charts.line_chart(
                    [
                        (date.fromisoformat(day), value)
                        for day, value in block["daily"][field]
                    ],
                    label=f"{labels.channel(name)} — {labels.page_field(field)}",
                    height=175,
                    colour=curve_colours[index % len(curve_colours)],
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
        ranked = performance.ranked(block["posts"])
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
                fallback = images.creative_from_permalink(
                    post["permalink"], fetcher=fetcher
                )
                if fallback:
                    sources = [fallback]
                    post["creative_from_permalink"] = True

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
                label=f"{labels.channel(name)} — teljesítmény a szokásoshoz képest",
                value_format=lambda value: _number(value, 1) + "×",
            )

    template = _environment().get_template("report.html.j2")
    return template.render(
        data=data,
        trends=trends,
        channel_posts=channel_posts,
        ranking=ranking,
        narrative=resolved,
        css=stylesheet(),
        logo_lockup=logo("hello-lockup"),
        logo_mark=logo("hello-mark"),
        period_hu=_period_hu(data["meta"]["period"]),
        generated=date.today().isoformat(),
        charts={
            "reach_split": charts.donut(
                [("Boostolt posztok", boosted), ("Organikus posztok", organic)],
                label="A poszt-elérés megoszlása",
            ),
        },
        currency=data["paid"]["currency"],
        manual=manual or {},
        manual_slots=manual_module.SLOTS,
        review_js=(TEMPLATES / "review.js").read_text(encoding="utf-8"),
    )
