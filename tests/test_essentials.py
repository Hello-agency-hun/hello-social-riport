"""Az Essentials riport: rövidebb, tíz dia, hagyományosabb rangsorral.

Egy másik social media manager kérte. A számokat ugyanaz a pipeline adja —
csak kevesebb kerül belőle a riportba, és a legjobb posztok sorrendje nem a
rezonancia-index, hanem az interakciók száma.
"""

from pipeline.kpi import engagement_breakdown
from pipeline.render import _essentials_posts, _template_name
from pipeline.schema import Post


def _post(**kwargs) -> Post:
    base = dict(
        channel="instagram",
        post_id="1",
        published=None,
        organic_measured=True,
    )
    base.update(kwargs)
    return Post(**base)


def test_engagement_breaks_down_by_type():
    posts = [
        _post(reactions=10, comments=2, shares=3, saves=4),
        _post(post_id="2", reactions=5, comments=1, shares=0, saves=1),
    ]
    out = engagement_breakdown(posts)
    assert out["reactions"] == 15
    assert out["comments"] == 3
    assert out["shares"] == 3
    assert out["saves"] == 5
    assert out["total"] == 26
    assert out["posts_counted"] == 2


def test_engagement_counts_only_measured_posts():
    """A ZoomSphere-ből ismert, de nem mért posztnak nincs interakciószáma.

    Nullaként beszámítani azt jelentené, hogy „mértük, és nem reagált rá
    senki" — pedig nem mértük.
    """
    posts = [
        _post(reactions=10),
        _post(post_id="2", organic_measured=False),
    ]
    assert engagement_breakdown(posts)["posts_counted"] == 1


def test_essentials_ranks_by_interactions_not_reach():
    """A hagyományosabb sorrend nem az elérés: azt a költés dönti el.

    A manager mindkét számot kéri a kártyán, de a rangsort az interakció adja.
    """
    big_reach = _post(post_id="nagy", reach=10000, reactions=1)
    engaging = _post(post_id="eros", reach=200, reactions=50, comments=5)
    selected = _essentials_posts([big_reach.__dict__, engaging.__dict__])
    assert [p["post_id"] for p in selected] == ["eros", "nagy"]


def test_essentials_shows_three_posts():
    posts = [_post(post_id=str(i), reactions=i).__dict__ for i in range(9)]
    assert len(_essentials_posts(posts)) == 3


def test_template_follows_the_variant():
    assert _template_name("essentials") == "report-essentials.html.j2"
    assert _template_name("full") == "report.html.j2"
    assert _template_name(None) == "report.html.j2"
    assert _template_name("ismeretlen") == "report.html.j2"
