import shutil

import pytest
import yaml

from pipeline import followers, kpi
from pipeline.build import build
from pipeline.errors import MissingConfigError


def test_a_missing_follower_count_stops_the_work(fixture_dir, tmp_path):
    """Kitölthető mezőként a riport végén állt, és pont ezért maradt üresen —
    oda már senki nem megy vissza. Fél perc leolvasni, tehát nem engedjük
    tovább nélküle."""
    work = tmp_path / "kovetok-nelkul"
    shutil.copytree(fixture_dir, work)
    config = yaml.safe_load((work / "client.yaml").read_text(encoding="utf-8"))
    del config["followers"]["instagram"]
    (work / "client.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )

    with pytest.raises(MissingConfigError) as caught:
        build(work, period="2026-07")

    message = str(caught.value)
    assert "instagram" in message
    assert "facebook" not in message, "csak azt kérjük, ami tényleg hiányzik"
    assert "profil" in message, "mondjuk meg, honnan olvasható le"


def test_a_channel_the_client_does_not_have_needs_no_follower_count(
    fixture_dir, tmp_path
):
    work = tmp_path / "csak-fb"
    shutil.copytree(fixture_dir, work)
    config = yaml.safe_load((work / "client.yaml").read_text(encoding="utf-8"))
    del config["client"]["ig_handle"]
    del config["followers"]["instagram"]
    (work / "client.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )

    assert build(work, period="2026-07")["audience"]["facebook"]["followers"] == 4187


def test_the_follower_count_produces_a_growth_rate():
    """Enélkül a követőszám csak egy szám a lapon, amiből semmi nem következik."""
    channels = {"facebook": {"totals": {"follows": 5}}}
    block = kpi.audience(channels, {"facebook": 4187})["facebook"]

    assert block["new_followers"] == 5
    # a hónap eleji állományhoz mérve, nem a hónap végihez
    assert block["growth"] == round(5 / 4182, 4)


def test_monthly_reach_stays_manual_but_gets_used(fixture_dir):
    """A havi elérés napi értékek összegéből nem áll elő — aki két napon látott
    minket, egy ember. Amit a menedzser beír, azt viszont felhasználjuk."""
    channels = {"facebook": {"totals": {"follows": 5}}}
    block = kpi.audience(channels, {"facebook": 4000}, {"facebook": 18000})["facebook"]

    assert block["monthly_reach"] == 18000
    assert block["reach_per_follower"] == 4.5


CONFIG = {"client": {"fb_page_id": "1", "ig_handle": "x"}}
CHANNELS = {
    "facebook": {"totals": {"follows": 5}},
    "instagram": {"totals": {}},
}


def _prev(period, facebook=4187, instagram=1962):
    return {
        "meta": {"period": period},
        "audience": {
            "facebook": {"followers": facebook},
            "instagram": {"followers": instagram},
        },
    }


def test_the_second_month_does_not_ask_again(fixture_dir):
    """A múlt havi állomány plusz a havi új követés kiadja a mostanit —
    nem kell minden hónapban újra leolvasni a profilról."""
    config = {"client": {"fb_page_id": "1"}}
    resolved, origin = followers.resolve(
        config, CHANNELS, _prev("2026-06"), period="2026-07"
    )

    assert resolved["facebook"] == 4187 + 5
    assert "továbbszámolva" in origin["facebook"]


def test_exact_contiguous_dates_chain_even_across_the_same_calendar_month():
    config = {"client": {"fb_page_id": "1"}}
    previous = _prev("2026-07")
    previous["meta"]["measurement_end"] = "2026-07-24"

    resolved, _ = followers.resolve(
        config,
        CHANNELS,
        previous,
        period="2026-08",
        measurement_start="2026-07-25",
    )

    assert resolved["facebook"] == 4187 + 5


def test_a_skipped_month_breaks_the_chain():
    """Ha kimarad egy hónap, a köztes gyarapodást senki nem mérte. A júliusi
    riportból a szeptemberi állomány nem jön ki."""
    config = {"client": {"fb_page_id": "1"}}

    with pytest.raises(MissingConfigError) as caught:
        followers.resolve(config, CHANNELS, _prev("2026-07"), period="2026-09")

    message = str(caught.value)
    assert "nem a közvetlenül megelőzőé" in message
    assert "2026-08" in message, "mondjuk meg, melyik hónap hiányzik"


def test_a_channel_without_daily_follows_still_has_to_be_asked():
    """Instagramon nincs napi követés-csempe: állomány + semmi = nem tudjuk."""
    with pytest.raises(MissingConfigError) as caught:
        followers.resolve(CONFIG, CHANNELS, _prev("2026-06"), period="2026-07")

    message = str(caught.value)
    assert "instagram" in message
    assert "facebook" not in message, "amit tudunk, azt ne kérdezzük újra"


def test_a_value_in_the_config_always_wins():
    """Ha a menedzser leolvasta, azt használjuk — a továbbszámolás csak pótlék."""
    config = {"client": {"fb_page_id": "1"}, "followers": {"facebook": 9999}}
    resolved, origin = followers.resolve(
        config, CHANNELS, _prev("2026-06"), period="2026-07"
    )

    assert resolved["facebook"] == 9999
    assert origin["facebook"] == "client.yaml"


def test_january_chains_back_to_december():
    assert followers.previous_period("2026-01") == "2025-12"
    assert followers.previous_period("2026-07") == "2026-06"


def test_audience_survives_a_channel_with_no_follow_data():
    """Instagramról nincs napi követés-csempe — ettől még a követőszám látszik."""
    block = kpi.audience({"instagram": {"totals": {}}}, {"instagram": 1962})["instagram"]

    assert block["followers"] == 1962
    assert block["new_followers"] is None
    assert block["growth"] is None
