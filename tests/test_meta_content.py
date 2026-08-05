from datetime import date

from pipeline.parsers.meta_content import parse


def test_parses_all_posts(input_file):
    assert len(parse(input_file("Jul-01-2026")).payload) == 16


def test_channel_is_derived_from_the_permalink(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    assert {p.channel for p in posts} == {"facebook"}


def test_top_post_metrics(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    top = max(posts, key=lambda p: p.reach)
    assert top.caption.startswith("Séfünk ajánlata!")
    assert top.reach == 9046
    assert top.views == 11810
    assert top.link_clicks == 1027


def test_post_id_has_no_page_prefix(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    assert all("_" not in p.post_id for p in posts)


def test_client_hints_carry_page_identity(input_file):
    hints = parse(input_file("Jul-01-2026")).client_hints
    assert hints["page_id"] == "100064824963030"
    assert hints["page_name"] == "Larus Étterem"


def test_period_spans_july(input_file):
    assert parse(input_file("Jul-01-2026")).period == (
        date(2026, 7, 1),
        date(2026, 7, 31),
    )
