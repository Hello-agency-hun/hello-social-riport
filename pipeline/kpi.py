from collections import Counter, defaultdict

from pipeline.guards import sum_additive, sum_results
from pipeline.schema import Campaign, ContentItem, DailySeries, Post


def content_summary(items: list[ContentItem]) -> dict:
    stories = Counter()
    for item in items:
        if item.post_type == "story":
            for channel in item.post_ids:
                stories[channel] += 1
    return {
        "total": len(items),
        "by_type": dict(Counter(item.post_type for item in items)),
        "stories_by_channel": dict(stories),
    }


def page_totals(series: list[DailySeries]) -> dict:
    totals: dict[str, dict[str, float]] = defaultdict(dict)
    for entry in series:
        totals[entry.channel][entry.field] = sum_additive(
            [value for _, value in entry.points], field=entry.field
        )
    return {channel: dict(fields) for channel, fields in totals.items()}


def paid_totals(campaigns: list[Campaign]) -> dict:
    always_on = [c for c in campaigns if not c.is_boost]
    boosted = [c for c in campaigns if c.is_boost]

    by_type: dict[str, dict] = {}
    grouped: dict[str, list[Campaign]] = defaultdict(list)
    for campaign in campaigns:
        if campaign.result_type:
            grouped[campaign.result_type].append(campaign)
    for result_type, group in grouped.items():
        by_type[result_type] = {
            "campaigns": len(group),
            "spend": sum(c.spend for c in group),
            "results": sum_results(group),
        }

    def block(group: list[Campaign]) -> dict:
        return {
            "campaigns": len(group),
            "spend": sum(c.spend for c in group),
            "impressions": sum(c.impressions for c in group),
            "link_clicks": sum(c.link_clicks for c in group),
        }

    return {
        "spend": sum(c.spend for c in campaigns),
        "currency": campaigns[0].currency if campaigns else "EUR",
        "always_on": block(always_on),
        "boosted": block(boosted),
        "by_result_type": by_type,
    }


def cross_channel(posts: list[Post]) -> dict:
    """A riport csúcspontja: mennyit ér a boost.

    A poszt-elérések összege szándékosan NEM havi reach — csak arányszámításra
    használjuk, és a riport is így címkézi.
    """
    boosted = [p for p in posts if p.is_boosted]
    organic = [p for p in posts if not p.is_boosted]

    boosted_reach = sum(p.reach for p in boosted)
    organic_reach = sum(p.reach for p in organic)
    total_reach = boosted_reach + organic_reach

    avg_organic = round(organic_reach / len(organic)) if organic else 0
    avg_boosted = round(boosted_reach / len(boosted)) if boosted else 0

    return {
        "posts_total": len(posts),
        "posts_boosted": len(boosted),
        "posts_organic": len(organic),
        "post_reach_sum": total_reach,
        "avg_reach_organic_post": avg_organic,
        "avg_reach_boosted_post": avg_boosted,
        "boosted_share_of_post_reach": (
            round(boosted_reach / total_reach, 3) if total_reach else 0.0
        ),
        "reach_multiplier": round(avg_boosted / avg_organic, 1) if avg_organic else 0.0,
        "boost_spend": sum(p.paid.spend for p in boosted),
    }


def channel_blocks(series: list, posts: list, campaigns: list) -> dict:
    """Csatornánként egy blokk: napi idősorok, összegek, posztok, boostok.

    A riport csatornánként külön szekciót kap, ezért az adat is így áll össze.
    Ami egy csatornáról nincs, az nem szerepel benne — nem nulla, nem üres kulcs.
    """
    blocks: dict[str, dict] = {}

    def block_for(channel: str) -> dict:
        return blocks.setdefault(
            channel, {"daily": {}, "totals": {}, "posts": [], "boosts": []}
        )

    for entry in series:
        block = block_for(entry.channel)
        block["daily"][entry.field] = [
            [day.isoformat(), value] for day, value in entry.points
        ]
        block["totals"][entry.field] = sum_additive(
            [value for _, value in entry.points], field=entry.field
        )

    for post in posts:
        block_for(post.channel)["posts"].append(post)

    for campaign in campaigns:
        if campaign.is_boost and campaign.channel:
            block_for(campaign.channel)["boosts"].append(campaign)

    return blocks
