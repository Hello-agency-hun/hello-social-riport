from datetime import date

import pytest

from pipeline.errors import ReachSummationError
from pipeline.join import join_posts
from pipeline.kpi import content_summary, cross_channel, page_totals, paid_totals
from pipeline.parsers import meta_ads, meta_content, meta_daily, zoomsphere
from pipeline.schema import DailySeries


@pytest.fixture
def posts(input_file):
    return join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    ).posts


def test_cross_channel_averages(posts):
    result = cross_channel(posts)
    assert result["avg_reach_organic_post"] == 130
    assert result["avg_reach_boosted_post"] == 4312
    assert result["boosted_share_of_post_reach"] == 0.917
    assert result["reach_multiplier"] == 33.2


def test_content_summary(input_file):
    items = zoomsphere.parse(input_file("Scheduler")).payload
    summary = content_summary(items)
    assert summary["total"] == 29
    assert summary["by_type"] == {"image": 14, "story": 14, "reel": 1}
    assert summary["stories_by_channel"] == {"facebook": 7, "instagram": 7}


def test_paid_totals_group_by_result_type(input_file):
    campaigns = meta_ads.parse(input_file("Kampányok")).payload.campaigns
    totals = paid_totals(campaigns)
    assert round(totals["spend"], 2) == 472.71
    assert totals["currency"] == "EUR"
    assert round(totals["always_on"]["spend"], 2) == 362.24
    assert round(totals["boosted"]["spend"], 2) == 110.47
    assert "actions:omni_landing_page_view" in totals["by_result_type"]


def test_page_totals_sum_additive_series(input_file):
    series = [
        meta_daily.parse(input_file(name)).payload
        for name in ("Felkeresések.csv", "Hivatkozáskattintások.csv", "Interakciók.csv")
    ]
    totals = page_totals(series)
    assert totals["facebook"]["visits"] == 1525
    assert totals["facebook"]["link_clicks"] == 1227
    assert totals["facebook"]["interactions"] == 345


def test_page_totals_refuse_to_sum_reach():
    """A havi reach nem áll elő napi értékek összegeként — a kód se tegye."""
    bad = DailySeries(
        channel="facebook",
        field="reach",
        metric="Elérés",
        points=[(date(2026, 7, 1), 100), (date(2026, 7, 2), 200)],
    )
    with pytest.raises(ReachSummationError):
        page_totals([bad])


def test_channel_block_groups_everything_by_channel(input_file):
    from pipeline.kpi import channel_blocks
    from pipeline.parsers import meta_daily

    series = [
        meta_daily.parse(input_file(name)).payload
        for name in (
            "Felkeresések.csv",
            "Hivatkozáskattintások.csv",
            "Interakciók.csv",
            "Követők.csv",
        )
    ]
    blocks = channel_blocks(series=series, posts=[], campaigns=[])
    facebook = blocks["facebook"]
    assert facebook["totals"]["visits"] == 1525
    assert facebook["totals"]["follows"] == 5
    assert len(facebook["daily"]["visits"]) == 31
    assert facebook["daily"]["visits"][0] == ["2026-07-01", 33]


def test_channel_block_omits_a_channel_without_data(input_file):
    from pipeline.kpi import channel_blocks
    from pipeline.parsers import meta_daily

    series = [meta_daily.parse(input_file("Felkeresések.csv")).payload]
    blocks = channel_blocks(series=series, posts=[], campaigns=[])
    assert "instagram" not in blocks
