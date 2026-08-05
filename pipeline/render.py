"""A riport összeállítása. Csak a `report_data.json`-t olvassa, forrásfájlt soha."""

from datetime import date
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import charts, images, labels
from pipeline import manual as manual_module
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
    resolved = narrative_module.resolve_all(narrative, data) if narrative else None

    organic = data["cross"]["organic_reach"]
    boosted = data["cross"]["boosted_reach"]

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
                ),
            )
            for field in sorted(block["daily"])
        ]

    channel_posts = {}
    for name, block in data.get("channels", {}).items():
        ranked = sorted(block["posts"], key=lambda post: -post["reach"])
        selected = [post for post in ranked if post["reach"]][:6]
        if not selected:
            # Ezen a csatornán nincs mért elérés — a boostoltakat emeljük ki,
            # mert azokról van mért fizetett adatunk.
            selected = [post for post in ranked if post.get("paid")][:6]
        for post in selected:
            uris = images.embed(
                post["creatives"][:1], cache_dir=cache_dir, fetcher=fetcher
            )
            post["thumb"] = uris[0] if uris else images.PLACEHOLDER
        channel_posts[name] = _balanced_chunks(selected)

    template = _environment().get_template("report.html.j2")
    return template.render(
        data=data,
        trends=trends,
        channel_posts=channel_posts,
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
