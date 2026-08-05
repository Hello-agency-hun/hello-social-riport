import pytest

from pipeline.errors import UnknownSourceError
from pipeline.parsers.meta_daily import parse


@pytest.mark.parametrize(
    "fragment, channel, field, total",
    [
        ("Felkeresések.csv", "facebook", "visits", 1525),
        ("Követők.csv", "facebook", "follows", 5),
        ("Interakciók.csv", "facebook", "interactions", 345),
        ("Hivatkozáskattintások.csv", "facebook", "link_clicks", 1227),
        ("Felkeresések-2.csv", "instagram", "visits", 634),
        ("Hivatkozáskattintások-2.csv", "instagram", "link_clicks", 389),
        ("Interakciók-2.csv", "instagram", "interactions", 255),
    ],
)
def test_known_metrics(input_file, fragment, channel, field, total):
    series = parse(input_file(fragment)).payload
    assert (series.channel, series.field) == (channel, field)
    assert series.total == total
    assert len(series.points) == 31


def test_unknown_metric_raises_with_the_metric_name(tmp_path):
    odd = tmp_path / "Valami.csv"
    odd.write_bytes(
        'sep=,\n"Teljesen új csempe"\n"Dátum","Primary"\n"2026-07-01T00:00:00","3"\n'.encode(
            "utf-16"
        )
    )
    with pytest.raises(UnknownSourceError, match="Teljesen új csempe"):
        parse(odd)


def test_channel_override_resolves_unknown_metric(tmp_path):
    odd = tmp_path / "Valami.csv"
    odd.write_bytes(
        'sep=,\n"Teljesen új csempe"\n"Dátum","Primary"\n"2026-07-01T00:00:00","3"\n'.encode(
            "utf-16"
        )
    )
    series = parse(odd, overrides={"Teljesen új csempe": ("facebook", "views")}).payload
    assert (series.channel, series.field, series.total) == ("facebook", "views", 3)


def test_real_overridden_metric(input_file):
    series = parse(
        input_file("Megtekintések-2.csv"),
        overrides={"Megtekintések": ("instagram", "views")},
    ).payload
    assert (series.channel, series.field) == ("instagram", "views")
    assert series.total == 22483
