import re
from dataclasses import dataclass, field, replace

from pipeline.errors import UnmatchedBoostError
from pipeline.schema import Campaign, ContentItem, Post

# A Meta a boost nevét a bejegyzés típusából állítja elő, de az ügyfelek egy
# része saját előtaggal nevezi a kampányait: `Mammut_Bejegyzés: „…”`. Amíg a
# levágás a sor elejéhez volt kötve, az előtag bennmaradt a kulcsban, és a
# boost nem talált posztot — a hirdetett poszt organikusként jelent volna meg,
# költés nélkül. Az előtag rövid és elválasztóval zárul, a poszt szövegébe
# ezért nem tud beleharapni.
BOOST_PREFIX = re.compile(
    r"^(?:[^\s:]{1,40}[_\-—:/])?(?:Instagram-bejegyzés|Bejegyzés):\s*"
)
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


def merge_boosts(first: Campaign, second: Campaign) -> Campaign:
    """Ugyanannak a posztnak két hirdetése — egy fizetett háttér.

    Egy posztot a hónapban többször is meg lehet hirdetni („Újbóli
    kiemelés”). Korábban a második kampány nem talált posztot, mert az első
    már lefoglalta, és a riport az ügyfélnek azt írta róla, hogy **korábbi
    hónapban megjelent** bejegyzést támogatott — ami nem igaz —, a költése
    pedig nem került a poszthoz.

    A költés, a megjelenés és a kattintás összeadható. Az elérés NEM: aki
    mindkét hirdetést látta, egy ember. Ezért a nagyobbik elérés marad — ez
    alsó becslés, de nem állít többet, mint amit mértünk. Eredményt csak
    azonos eredménytípusnál adunk össze (lásd `guards.sum_results`); eltérő
    típusnál a nagyobb költésű kampányé marad.
    """
    lead, other = (first, second) if first.spend >= second.spend else (second, first)
    same_type = first.result_type == second.result_type
    ongoing = first.is_ongoing or second.is_ongoing
    starts = [day for day in (first.start_date, second.start_date) if day]
    ends = [day for day in (first.end_date, second.end_date) if day]
    return replace(
        lead,
        spend=round(first.spend + second.spend, 2),
        impressions=first.impressions + second.impressions,
        reach=max(first.reach, second.reach),
        link_clicks=first.link_clicks + second.link_clicks,
        results=first.results + second.results if same_type else lead.results,
        cost_per_result=(
            round((first.spend + second.spend) / (first.results + second.results), 2)
            if same_type and first.results + second.results
            else lead.cost_per_result
        ),
        start_date=min(starts) if starts else None,
        end_date=None if ongoing or not ends else max(ends),
        is_ongoing=ongoing,
    )


def _boost_candidates(campaign: Campaign, key: str, posts: list[Post], captions: dict) -> list[Post]:
    """A kampányhoz illő posztok, a legerősebb egyezéssel kezdve.

    A kampány neve a poszt szövegének ELEJE, tehát az előtag-egyezés az erős
    bizonyíték. A „valahol benne van” csak tartalék: egy rövid kampánynév
    („Ennyi!”) egy másik poszt szövegének közepén is előfordulhat, és akkor a
    költés rossz poszthoz kerülne.
    """
    same_channel = [post for post in posts if post.channel == campaign.channel]
    prefix = [post for post in same_channel if captions[id(post)].startswith(key)]
    taken = {id(post) for post in prefix}
    inside = [
        post
        for post in same_channel
        if id(post) not in taken and key in captions[id(post)]
    ]
    return prefix + inside


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

    # Tartalék: szöveg szerint. A poszt-azonosító a megbízhatóbb, de a két
    # rendszer nem mindig ugyanazt az ID-t tárolja — Instagramnál különösen —,
    # és ha nem egyezik, a poszt NÉMÁN elveszti a kreatívját. A szöveg egyezése
    # gyengébb bizonyíték, de sokkal jobb, mint egy üres kép.
    by_caption: dict[tuple[str, str], ContentItem] = {}
    for item in items:
        for channel in ("facebook", "instagram"):
            key = normalize_caption(item.caption(channel))[:MATCH_LENGTH]
            if key and item.creatives.get(channel):
                by_caption.setdefault((channel, key), item)

    for post in result.posts:
        item = by_id.get((post.channel, post.post_id))
        if item is None:
            key = normalize_caption(post.caption)[:MATCH_LENGTH]
            item = by_caption.get((post.channel, key)) if key else None
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

    # 2. Meta Ads boostok → caption-prefix alapján. A normalizált szöveget
    # posztonként egyszer számoljuk, nem boostonként újra.
    captions = {id(post): normalize_caption(post.caption) for post in result.posts}
    for campaign in campaigns:
        if not campaign.is_boost:
            continue
        key = normalize_caption(campaign.name)[:MATCH_LENGTH]
        if not key:
            result.unmatched_boosts.append(campaign)
            continue
        candidates = _boost_candidates(campaign, key, result.posts, captions)
        # Előbb a még hirdetés nélküli posztok: két azonos kezdetű poszt
        # (heti menü) két boostja így két posztra kerül, nem egyre.
        match = next((post for post in candidates if post.paid is None), None)
        if match is not None:
            match.paid = campaign
        elif candidates:
            # Újbóli kiemelés: a poszt ebben a hónapban jelent meg, és már van
            # hirdetése. Nem „korábbi poszt” — a költése ehhez a poszthoz tartozik.
            candidates[0].paid = merge_boosts(candidates[0].paid, campaign)
        else:
            result.unmatched_boosts.append(campaign)

    if strict and result.unmatched_boosts:
        names = ", ".join(c.name for c in result.unmatched_boosts)
        raise UnmatchedBoostError(
            f"nem illeszthető boostolt poszt: {names}. "
            "Ellenőrizd, hogy a Tartalom export ugyanarra a hónapra és csatornára szól-e."
        )

    return result
