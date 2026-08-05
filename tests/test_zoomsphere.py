from collections import Counter
from datetime import date

from pipeline.parsers.zoomsphere import parse


def test_parses_all_rows(input_file):
    source = parse(input_file("Scheduler"))
    assert len(source.payload) == 29


def test_post_type_distribution(input_file):
    types = Counter(item.post_type for item in parse(input_file("Scheduler")).payload)
    assert types == {"image": 14, "story": 14, "reel": 1}


def test_period_is_july(input_file):
    source = parse(input_file("Scheduler"))
    assert source.period == (date(2026, 7, 1), date(2026, 7, 29))


def test_facebook_post_id_keeps_only_the_suffix(input_file):
    items = parse(input_file("Scheduler")).payload
    first = next(i for i in items if i.published == date(2026, 7, 1))
    assert first.post_ids["facebook"] == "1490635643107254"
    assert first.post_ids["instagram"] == "17957904336154653"


def test_creative_urls_are_split(input_file):
    items = parse(input_file("Scheduler")).payload
    first = next(i for i in items if i.published == date(2026, 7, 1))
    assert len(first.creatives["instagram"]) == 2
    assert all(url.startswith("https://") for url in first.creatives["instagram"])


def test_client_hint_carries_page_name(input_file):
    assert parse(input_file("Scheduler")).client_hints["page_name"] == "Larus Étterem"


def test_video_posts_lead_with_a_still_not_the_mp4(input_file):
    """A reel nyers fájlja mp4 — abból nem lesz thumbnail a riportban.

    A ZoomSphere ad poszter-képet is; annak kell a lista élén állnia, különben
    a Top posztok oldalon helyőrző jelenne meg a kreatív helyett.
    """
    items = parse(input_file("Scheduler")).payload
    reel = next(item for item in items if item.post_type == "reel")
    for channel, urls in reel.creatives.items():
        assert urls, f"{channel}: a reelnek van kreatívja"
        assert "/offset-thumbs/" in urls[0] or "thumb" in urls[0].lower() or not urls[0].endswith(
            (".mp4", ".mov")
        ), f"{channel}: az első kreatív nem lehet videófájl — {urls[0]}"
