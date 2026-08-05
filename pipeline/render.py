"""A riport összeállítása. Csak a `report_data.json`-t olvassa, forrásfájlt soha."""

from datetime import date
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import charts, images, labels
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


def _organic_reach(posts: list[dict]) -> int:
    return sum(post["reach"] for post in posts if post.get("paid") is None)


def render(
    data: dict,
    cache_dir: Path,
    narrative: dict | None = None,
    fetcher: Callable[[str], bytes] = images.fetch,
) -> str:
    posts = sorted(data["posts"], key=lambda post: -post["reach"])

    for post in posts:
        uris = images.embed(post["creatives"][:1], cache_dir=cache_dir, fetcher=fetcher)
        post["thumb"] = uris[0] if uris else images.PLACEHOLDER

    organic = _organic_reach(posts)
    boosted = data["cross"]["post_reach_sum"] - organic

    template = _environment().get_template("report.html.j2")
    return template.render(
        data=data,
        posts=posts,
        narrative=narrative,
        css=stylesheet(),
        logo_lockup=logo("hello-lockup"),
        logo_mark=logo("hello-mark"),
        period_hu=_period_hu(data["meta"]["period"]),
        generated=date.today().isoformat(),
        page_fields=sorted(
            {field for fields in data["page"].values() for field in fields}
        ),
        charts={
            "reach_split": charts.donut(
                [("Boostolt posztok", boosted), ("Organikus posztok", organic)],
                label="A poszt-elérés megoszlása",
            ),
            "top_posts": charts.bar_chart(
                [
                    (post["caption"][:34] or "(nincs szöveg)", post["reach"])
                    for post in posts[:6]
                ],
                label="A hat legnagyobb elérésű poszt",
            ),
        },
        currency=data["paid"]["currency"],
    )
