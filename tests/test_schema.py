from datetime import date

from pipeline.schema import Campaign, ContentItem, DailySeries, Post


def test_daily_series_total_sums_values():
    series = DailySeries(
        channel="facebook",
        field="link_clicks",
        metric="Facebookos hivatkozáskattintások",
        points=[(date(2026, 7, 1), 10), (date(2026, 7, 2), 5)],
    )
    assert series.total == 15


def test_post_is_boosted_when_paid_present():
    post = Post(channel="facebook", post_id="1", published=date(2026, 7, 1))
    assert post.is_boosted is False
    post.paid = Campaign(name="Bejegyzés: „x”", spend=13.9, currency="EUR")
    assert post.is_boosted is True


def test_content_item_prefers_channel_specific_caption():
    item = ContentItem(
        published=date(2026, 7, 1),
        post_type="image",
        captions={"facebook": "FB szöveg", "instagram": "IG szöveg"},
    )
    assert item.caption("instagram") == "IG szöveg"
    assert item.caption("facebook") == "FB szöveg"
