import pytest

from pipeline.errors import UnmatchedBoostError
from pipeline.join import join_posts, normalize_caption
from pipeline.parsers import meta_ads, meta_content, zoomsphere
from pipeline.schema import Campaign


def test_caption_normalisation_strips_prefix_and_quotes():
    assert normalize_caption('Bejegyzés: „Séfünk ajánlata! 😎”') == "séfünk ajánlata! 😎"
    assert normalize_caption("Instagram-bejegyzés: Ennyi! 😉🥂 #larus") == "ennyi! 😉🥂 #larus"
    assert normalize_caption("Nyári napok,   terasz...") == "nyári napok, terasz"


@pytest.fixture
def joined(input_file):
    return join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    )


def test_zoomsphere_matches_15_of_16_posts(joined):
    """16 Facebook-poszt a Tartalom exportból, plusz 15 Instagram-poszt a
    ZoomSphere-ből épül fel (Task 2) — összesen 31, 30 kreatívval."""
    assert len(joined.posts) == 31
    assert sum(1 for p in joined.posts if p.creatives) == 30


def test_facebook_boosts_are_matched(joined):
    boosted = [p for p in joined.posts if p.is_boosted]
    assert len(boosted) == 8


def test_instagram_boosts_are_reported_as_unmatched(joined):
    """A ZoomSphere-ből épülő IG-posztoknak köszönhetően (Task 2) a 4 IG boost
    mostantól illeszthető — a pipeline már nem jelenti unmatched-ként."""
    unmatched = [c.name for c in joined.unmatched_boosts]
    assert unmatched == []


def test_boost_carries_spend_and_paid_reach(joined):
    top = max(joined.posts, key=lambda p: p.reach)
    assert top.caption.startswith("Séfünk ajánlata!")
    assert top.paid.spend == 15.95
    assert top.paid.reach == 8398


def test_boosted_posts_dominate_reach(joined):
    boosted = sum(p.reach for p in joined.posts if p.is_boosted)
    total = sum(p.reach for p in joined.posts)
    assert total == 18811
    assert round(boosted / total, 3) == 0.917


def test_unmatched_boost_is_reported_not_guessed():
    orphan = Campaign(
        name="Bejegyzés: „Ez a poszt nem létezik”",
        spend=5.0,
        channel="facebook",
        is_boost=True,
    )
    result = join_posts(content=[], items=[], campaigns=[orphan])
    assert [c.name for c in result.unmatched_boosts] == [orphan.name]

    with pytest.raises(UnmatchedBoostError, match="nem létezik"):
        join_posts(content=[], items=[], campaigns=[orphan], strict=True)


def test_instagram_posts_are_built_from_zoomsphere(input_file):
    """IG Tartalom export nélkül is meg tudjuk mutatni a boostolt IG-posztokat."""
    result = join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    )
    instagram = [post for post in result.posts if post.channel == "instagram"]
    boosted = [post for post in instagram if post.is_boosted]
    assert len(boosted) == 4
    assert result.unmatched_boosts == []
    for post in boosted:
        assert post.creatives, "kreatív nélkül nincs értelme megmutatni"
        assert post.caption
        assert post.reach == 0, "IG organikus elérés nincs mérve — nem találjuk ki"


def test_facebook_posts_still_come_from_the_content_export(input_file):
    result = join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    )
    facebook = [post for post in result.posts if post.channel == "facebook"]
    assert len(facebook) == 16
    assert max(post.reach for post in facebook) == 9046


def test_stories_are_not_turned_into_posts(input_file):
    """A story külön műfaj, és nincs hozzá teljesítményadat sehol."""
    result = join_posts(
        content=[],
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=[],
    )
    assert all(post.post_type != "story" for post in result.posts)


def test_client_prefix_is_stripped_from_the_boost_name():
    """`Mammut_Bejegyzés: „…”` — az ügyfél előtagja a boost neve előtt áll.

    Amíg a levágás a sor elejéhez volt kötve, az előtag bennmaradt a kulcsban,
    és egyetlen boost sem talált posztot: a hirdetett posztok organikusként
    jelentek volna meg, hirdetési költség nélkül.
    """
    from pipeline.join import normalize_caption

    assert normalize_caption("Mammut_Bejegyzés: „Nyáron is irány a Mammut!”") == (
        normalize_caption("Bejegyzés: „Nyáron is irány a Mammut!”")
    )
    assert normalize_caption("Mammut_Instagram-bejegyzés: Hangolódj a nyári…") == (
        normalize_caption("Instagram-bejegyzés: Hangolódj a nyári…")
    )


def test_a_caption_that_merely_mentions_the_word_is_left_alone():
    """A levágás nem ehet bele a poszt szövegébe."""
    from pipeline.join import normalize_caption

    assert normalize_caption("Ez a bejegyzés: nyári nyitvatartás") == (
        "ez a bejegyzés: nyári nyitvatartás"
    )


def _fb_post(post_id: str, caption: str):
    from datetime import date

    from pipeline.schema import Post

    return Post(
        channel="facebook",
        post_id=post_id,
        published=date(2026, 7, 3),
        caption=caption,
        reach=100,
        organic_measured=True,
    )


def _boost(caption: str, spend: float, reach: int, result_type: str = "reach", results: int = 0):
    return Campaign(
        name=f"Bejegyzés: „{caption}”",
        spend=spend,
        reach=reach,
        impressions=reach * 2,
        link_clicks=3,
        results=results,
        result_type=result_type,
        channel="facebook",
        is_boost=True,
    )


def test_a_post_boosted_twice_keeps_both_spends():
    """Egy poszt kétszeri meghirdetése nem „korábbi poszt”.

    A második kampány korábban nem talált posztot (az elsőt már lefoglalta),
    és a riport az ügyfélnek azt írta, hogy egy korábbi hónapban megjelent
    bejegyzést támogattunk — a költése pedig nem került a poszthoz.
    """
    post = _fb_post("1", "Nyári menü a teraszon, minden hétvégén")
    first = _boost("Nyári menü a teraszon, minden hétvégén", 10.0, 1000, results=50)
    second = _boost("Nyári menü a teraszon, minden hétvégén", 5.5, 1500, results=20)

    joined = join_posts(content=[post], items=[], campaigns=[first, second])

    assert joined.unmatched_boosts == []
    paid = joined.posts[0].paid
    assert paid.spend == 15.5
    assert paid.impressions == 5000
    assert paid.link_clicks == 6
    # Az elérés nem adható össze: aki mindkettőt látta, egy ember.
    assert paid.reach == 1500
    assert paid.results == 70


def test_reboost_with_a_different_result_type_does_not_add_results():
    post = _fb_post("1", "Nyári menü a teraszon, minden hétvégén")
    first = _boost("Nyári menü a teraszon, minden hétvégén", 10.0, 1000, "reach", 900)
    second = _boost("Nyári menü a teraszon, minden hétvégén", 4.0, 800, "actions:link_click", 12)

    paid = join_posts(content=[post], items=[], campaigns=[first, second]).posts[0].paid

    assert paid.spend == 14.0
    assert (paid.result_type, paid.results) == ("reach", 900)


def test_two_posts_with_the_same_opening_get_one_boost_each():
    """Heti visszatérő poszt: két boost két posztra kerül, nem egyre."""
    week_one = _fb_post("1", "Heti menü: gulyás, rántott hús")
    week_two = _fb_post("2", "Heti menü: gulyás, rántott hús")
    boosts = [
        _boost("Heti menü: gulyás, rántott hús", 7.0, 700),
        _boost("Heti menü: gulyás, rántott hús", 8.0, 800),
    ]

    joined = join_posts(content=[week_one, week_two], items=[], campaigns=boosts)

    assert [post.paid.spend for post in joined.posts] == [7.0, 8.0]


def test_prefix_match_wins_over_a_mention_inside_another_caption():
    """Egy rövid kampánynév egy másik poszt szövegének közepén is
    előfordulhat — a költés akkor is ahhoz a poszthoz kerüljön, amelyik
    ezzel a szöveggel KEZDŐDIK."""
    mention = _fb_post("1", "Hétvégén is várunk! Ennyi! A többit a helyszínen")
    real = _fb_post("2", "Ennyi! Nyár, terasz, limonádé")

    joined = join_posts(
        content=[mention, real], items=[], campaigns=[_boost("Ennyi!", 9.0, 900)]
    )

    assert joined.posts[0].paid is None
    assert joined.posts[1].paid.spend == 9.0
