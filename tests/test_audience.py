import shutil

import pytest
import yaml

from pipeline import kpi
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
    block = kpi.audience(channels, {"facebook": 4000}, {"reach_facebook": 18000})["facebook"]

    assert block["monthly_reach"] == 18000
    assert block["reach_per_follower"] == 4.5


def test_audience_survives_a_channel_with_no_follow_data():
    """Instagramról nincs napi követés-csempe — ettől még a követőszám látszik."""
    block = kpi.audience({"instagram": {"totals": {}}}, {"instagram": 1962})["instagram"]

    assert block["followers"] == 1962
    assert block["new_followers"] is None
    assert block["growth"] is None
