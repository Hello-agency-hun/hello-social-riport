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
    assert len(joined.posts) == 16
    assert sum(1 for p in joined.posts if p.creatives) == 15


def test_facebook_boosts_are_matched(joined):
    boosted = [p for p in joined.posts if p.is_boosted]
    assert len(boosted) == 4


def test_instagram_boosts_are_reported_as_unmatched(joined):
    """A referencia-készletben nincs IG Tartalom export, ezért a 4 IG boost
    nem illeszthető. A pipeline ezt jelenti, nem találgat."""
    unmatched = [c.name for c in joined.unmatched_boosts]
    assert len(unmatched) == 4
    assert all(name.startswith("Instagram-bejegyzés:") for name in unmatched)


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
