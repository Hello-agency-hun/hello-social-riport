"""Az Essentials riport: rövidebb, tíz dia, hagyományosabb rangsorral.

Egy másik social media manager kérte. A számokat ugyanaz a pipeline adja —
csak kevesebb kerül belőle a riportba, és a legjobb posztok sorrendje nem a
rezonancia-index, hanem az interakciók száma.
"""

from datetime import date
from pathlib import Path

from pipeline.build import _essentials_missing
from pipeline.kpi import audience, engagement_breakdown
from pipeline.render import _essentials_posts, _template_name
from pipeline.schema import DailySeries, Post


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


def test_essentials_names_every_missing_traditional_metric():
    config = {"report": {"variant": "essentials"}}
    client = {"fb_page_id": "123"}
    series = [
        DailySeries(
            channel="facebook",
            field="views",
            metric="Megtekintések",
            points=[(date(2026, 7, 1), 10)],
        )
    ]

    missing = _essentials_missing(config, client, {"facebook": "content.csv"}, series)

    assert any("Facebook" in item and "Interakciók" in item for item in missing)
    assert any("Facebook" in item and "Felkeresések" in item for item in missing)
    assert any("Facebook" in item and "Hivatkozáskattintások" in item for item in missing)
    assert any("Facebook" in item and "Új követők" in item for item in missing)
    assert not any("Megjelenések" in item for item in missing)


def test_full_report_does_not_gain_essentials_only_blockers():
    assert _essentials_missing(
        {"report": {"variant": "full"}},
        {"fb_page_id": "123"},
        {},
        [],
    ) == []


def test_previous_and_current_followers_satisfy_growth_without_follows_tile():
    config = {
        "report": {"variant": "essentials"},
        "followers": {"facebook": 110},
    }
    client = {"fb_page_id": "123"}
    series = [
        DailySeries("facebook", field, field, [(date(2026, 7, 1), 1)])
        for field in ("views", "interactions", "visits", "link_clicks")
    ]
    previous = {"audience": {"facebook": {"followers": 100}}}

    missing = _essentials_missing(
        config,
        client,
        {"facebook": "content.csv"},
        series,
        previous=previous,
    )

    assert missing == []


def test_audience_growth_can_use_previous_follower_total():
    result = audience(
        {"facebook": {"totals": {}}},
        {"facebook": 110},
        previous_audience={"facebook": {"followers": 100}},
    )

    assert result["facebook"]["new_followers"] == 10
    assert result["facebook"]["growth"] == 0.1


def test_essentials_template_keeps_zero_saves_visible():
    source = (Path(__file__).parents[1] / "templates" / "report-essentials.html.j2").read_text(
        encoding="utf-8"
    )

    assert "{% if post.saves %}" not in source
    assert "{% if block.engagement.saves %}" not in source
    assert "t.essentials_impressions" in source
