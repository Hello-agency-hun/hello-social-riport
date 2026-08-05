from datetime import date

from pipeline.parsers.meta_ads import detect_currency, parse


def test_currency_is_read_from_the_header():
    assert detect_currency(["Eredmények", "Elköltött összeg (EUR)"]) == "EUR"
    assert detect_currency(["Elköltött összeg (HUF)"]) == "HUF"


def test_zero_rows_are_filtered_and_counted(input_file):
    source = parse(input_file("Kampányok"))
    assert len(source.payload.campaigns) == 13
    assert source.payload.dropped_zero_rows == 16


def test_boosts_and_always_on_are_separated(input_file):
    campaigns = parse(input_file("Kampányok")).payload.campaigns
    boosts = [c for c in campaigns if c.is_boost]
    always_on = [c for c in campaigns if not c.is_boost]
    assert len(boosts) == 8
    assert len(always_on) == 5


def test_boost_channel_comes_from_the_name_prefix(input_file):
    boosts = [c for c in parse(input_file("Kampányok")).payload.campaigns if c.is_boost]
    assert sum(1 for c in boosts if c.channel == "instagram") == 4
    assert sum(1 for c in boosts if c.channel == "facebook") == 4


def test_total_spend(input_file):
    campaigns = parse(input_file("Kampányok")).payload.campaigns
    assert round(sum(c.spend for c in campaigns), 2) == 472.71


def test_result_types_are_preserved(input_file):
    campaigns = parse(input_file("Kampányok")).payload.campaigns
    assert {c.result_type for c in campaigns} == {
        "reach",
        "actions:omni_landing_page_view",
        "profile_visit_view",
        "actions:post_engagement",
        "actions:link_click",
        "actions:click_to_call_native_call_placed",
    }


def test_period(input_file):
    assert parse(input_file("Kampányok")).period == (date(2026, 7, 1), date(2026, 7, 31))
