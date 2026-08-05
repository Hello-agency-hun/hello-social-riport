from collections import Counter

from pipeline.detect import identify, scan


def test_identifies_every_fixture_file(input_dir):
    kinds = Counter(item.kind for item in scan(input_dir))
    assert kinds == {
        "zoomsphere": 1,
        "meta_ads": 1,
        "meta_content": 1,
        "meta_daily": 8,
    }


def test_daily_metric_name_comes_from_second_line(input_file):
    item = identify(input_file("Interakciók-2.csv"))
    assert item.kind == "meta_daily"
    assert item.metric == "Interakció tartalmaknál"
    assert item.channel == "instagram"


def test_filename_is_not_used_for_identification(input_file):
    a = identify(input_file("Felkeresések.csv"))
    b = identify(input_file("Felkeresések-2.csv"))
    assert (a.metric, a.channel) == ("Facebook-felkeresések", "facebook")
    assert (b.metric, b.channel) == ("Instagram-profilfelkeresések", "instagram")


def test_unknown_daily_metric_is_reported_not_fatal(tmp_path):
    odd = tmp_path / "Valami.csv"
    odd.write_bytes('sep=,\n"Teljesen új csempe"\n"Dátum","Primary"\n'.encode("utf-16"))
    item = identify(odd)
    assert item.kind == "meta_daily"
    assert item.metric == "Teljesen új csempe"
    assert item.channel is None
