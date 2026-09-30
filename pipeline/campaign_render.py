"""Offline-capable HTML rendering of a standalone campaign report."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import images
from pipeline.assets import TEMPLATES, logo, stylesheet
from pipeline.errors import NarrativeError
from pipeline.render import _number


NARRATIVE_KEYS = ("executive_summary", "what_worked", "next_steps")


def check_narrative(narrative):
    narrative = narrative or {}
    if not isinstance(narrative, dict):
        raise NarrativeError("A kampány narratívája mezőnkénti JSON-objektum legyen.")
    for key, value in narrative.items():
        if key not in NARRATIVE_KEYS or not isinstance(value, str):
            raise NarrativeError(f"Ismeretlen vagy nem szöveges kampánynarratíva: {key}")
        if any(character.isdigit() for character in value):
            raise NarrativeError(
                f"A(z) {key} narratívában kézzel írt szám szerepel. "
                "A számok a lezárt adatblokkokban maradnak; a szövegben fogalmazz számjegyek nélkül."
            )
    return narrative


def _chunks(items, size):
    return [items[index:index + size] for index in range(0, len(items), size)]


def render_campaign(data, narrative=None, cache_dir=None, fetcher=images.fetch, variant=None):
    narrative = check_narrative(narrative)
    selected_variant = variant or data["meta"]["variant"]
    if selected_variant not in ("full", "essentials"):
        raise NarrativeError("Ismeretlen kampányriport-változat.")
    cache = Path(cache_dir or ".image-cache")
    posts = list(data["posts"])
    if selected_variant == "essentials":
        # No invented ranking: measured interactions only, otherwise chronology.
        posts = sorted(posts, key=lambda post: (
            post["metrics_measured"],
            sum(post.get(key) or 0 for key in ("reactions", "comments", "shares", "saves")),
            post["published"],
        ), reverse=True)[:3]
    rendered_posts = []
    for post in posts:
        row = dict(post)
        row["image"], row["creative_recovery"] = images.thumbnail(
            row.get("creatives"), row.get("permalink", ""), cache, fetcher
        )
        rendered_posts.append(row)
    ad_rows = data["ads"] if selected_variant == "full" else data["ads"][:5]
    monthly = [{"month": month, **values} for month, values in data["monthly"].items()]
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    environment.filters["num"] = lambda value: _number(value)
    environment.filters["money"] = lambda value: _number(value, 2)
    return environment.get_template("campaign.html.j2").render(
        data=data,
        narrative=narrative,
        variant=selected_variant,
        monthly_pages=_chunks(monthly, 6),
        unallocated_pages=_chunks(data["unallocated_ads"], 7),
        ad_pages=_chunks(ad_rows, 7),
        post_pages=_chunks(rendered_posts, 3),
        kpi_pages=_chunks(data["kpis"], 6),
        warning_pages=_chunks(data["warnings"], 7),
        css=stylesheet(),
        logo_lockup=logo("hello-lockup"),
    )
