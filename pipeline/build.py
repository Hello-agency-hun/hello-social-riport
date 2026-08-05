from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path

import yaml

from pipeline import compare, guards, kpi
from pipeline.detect import scan
from pipeline.errors import DuplicateSourceError, UnknownSourceError
from pipeline.join import join_posts
from pipeline.parsers import meta_ads, meta_content, meta_daily, zoomsphere


# Ezekből pontosan egy tartozik egy hónaphoz. A `meta_content` és a `meta_daily`
# szándékosan nincs itt: előbbiből csatornánként, utóbbiból metrikánként jön egy.
SINGLETON_SOURCES = {
    "zoomsphere": "ZoomSphere export",
    "meta_ads": "Meta Ads export",
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
    path = Path(directory) / "client.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
    seen: dict[str, str] = {}

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
            content += parsed.payload
        elif source.kind == "meta_daily":
            parsed = meta_daily.parse(source.path, overrides=overrides)
            series.append(parsed.payload)
        else:
            unknown.append(source.path.name)
            continue

        guards.check_period(source.kind, parsed.period, period)
        hints.update({k: v for k, v in parsed.client_hints.items() if v})

    if unknown:
        raise UnknownSourceError("nem azonosítható fájl: " + ", ".join(unknown))

    guards.check_client(hints, client)

    joined = join_posts(content=content, items=items, campaigns=campaigns)

    channels = kpi.channel_blocks(
        series=series, posts=joined.posts, campaigns=campaigns
    )
    previous = compare.load_previous(directory)

    return _serialise(
        {
            "meta": {
                "client": client["name"],
                "period": period,
                "currency": ads_payload.currency if ads_payload else "EUR",
                "language": config.get("report", {}).get("language", "hu"),
            },
            "content": kpi.content_summary(items),
            # A posztok egyetlen helyen élnek: a csatorna-blokkokban. Lapos
            # másolatot nem tartunk mellette — két forrás ugyanarra elcsúszik.
            "channels": channels,
            "comparison": {
                name: compare.deltas(
                    block["totals"],
                    (previous or {}).get("channels", {}).get(name, {}).get("totals", {}),
                )
                for name, block in channels.items()
            },
            "paid": kpi.paid_totals(campaigns),
            "cross": kpi.cross_channel(joined.posts),
            "quality": {
                "posts_with_creative": sum(1 for p in joined.posts if p.creatives),
                "posts_total": len(joined.posts),
                "posts_measured": sum(1 for p in joined.posts if p.organic_measured),
                "unmatched_boosts": [c.name for c in joined.unmatched_boosts],
                "unmatched_content": [p.post_id for p in joined.unmatched_content],
                "dropped_zero_campaign_rows": (
                    ads_payload.dropped_zero_rows if ads_payload else 0
                ),
            },
        }
    )
