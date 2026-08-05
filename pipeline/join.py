import re
from dataclasses import dataclass, field

from pipeline.errors import UnmatchedBoostError
from pipeline.schema import Campaign, ContentItem, Post

BOOST_PREFIX = re.compile(r"^(Instagram-bejegyzés:|Bejegyzés:)\s*")
MATCH_LENGTH = 30


@dataclass
class JoinResult:
    posts: list[Post] = field(default_factory=list)
    unmatched_boosts: list[Campaign] = field(default_factory=list)
    unmatched_content: list[Post] = field(default_factory=list)


def normalize_caption(text: str) -> str:
    """A boostolt kampány neve a poszt szövegének csonkolt változata."""
    text = BOOST_PREFIX.sub("", text or "")
    text = text.strip().strip("„”\"'")
    text = text.replace("…", "").replace("...", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def join_posts(
    content: list[Post],
    items: list[ContentItem],
    campaigns: list[Campaign],
    strict: bool = False,
) -> JoinResult:
    result = JoinResult(posts=list(content))

    # 1. ZoomSphere → kreatív, permalink, poszttípus, poszt-ID alapján
    by_id: dict[tuple[str, str], ContentItem] = {}
    for item in items:
        for channel, post_id in item.post_ids.items():
            if post_id:
                by_id[(channel, post_id)] = item

    for post in result.posts:
        item = by_id.get((post.channel, post.post_id))
        if item is None:
            result.unmatched_content.append(post)
            continue
        post.creatives = item.creatives.get(post.channel, [])
        post.post_type = post.post_type or item.post_type
        post.permalink = post.permalink or item.permalinks.get(post.channel, "")

    # 1b. Amelyik csatornáról nincs Tartalom export, ott a ZoomSphere-ből
    # építünk poszt-objektumot: kreatív, szöveg, link. Organikus metrika nélkül
    # — azt nem méri semmi, tehát nem találjuk ki.
    measured = {post.channel for post in result.posts}
    for item in items:
        if item.post_type == "story":
            continue
        for channel, post_id in item.post_ids.items():
            if not post_id or channel in measured:
                continue
            result.posts.append(
                Post(
                    channel=channel,
                    post_id=post_id,
                    published=item.published,
                    caption=item.caption(channel),
                    permalink=item.permalinks.get(channel, ""),
                    post_type=item.post_type,
                    creatives=item.creatives.get(channel, []),
                )
            )

    # 2. Meta Ads boostok → caption-prefix alapján
    for campaign in campaigns:
        if not campaign.is_boost:
            continue
        key = normalize_caption(campaign.name)[:MATCH_LENGTH]
        if not key:
            result.unmatched_boosts.append(campaign)
            continue
        match = next(
            (
                post
                for post in result.posts
                if post.channel == campaign.channel
                and post.paid is None
                and key in normalize_caption(post.caption)
            ),
            None,
        )
        if match is None:
            result.unmatched_boosts.append(campaign)
        else:
            match.paid = campaign

    if strict and result.unmatched_boosts:
        names = ", ".join(c.name for c in result.unmatched_boosts)
        raise UnmatchedBoostError(
            f"nem illeszthető boostolt poszt: {names}. "
            "Ellenőrizd, hogy a Tartalom export ugyanarra a hónapra és csatornára szól-e."
        )

    return result
