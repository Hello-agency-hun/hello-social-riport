from datetime import date

import pytest

from pipeline.errors import PipelineError, UnknownSourceError
from pipeline.periods import filter_daily
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


def _write(path, body: str):
    path.write_bytes(body.encode("utf-16"))
    return path


def test_truncated_file_raises_a_pipeline_error(tmp_path):
    """A CLI csak PipelineError-t fog el — a nyers IndexError értelmezhetetlen lenne."""
    truncated = _write(tmp_path / "Csonka.csv", 'sep=,\n"Facebook-felkeresések"\n')
    with pytest.raises(PipelineError, match="csonka"):
        parse(truncated)


def test_malformed_date_row_names_the_row(tmp_path):
    bad = _write(
        tmp_path / "Rossz.csv",
        'sep=,\n"Facebook-felkeresések"\n"Dátum","Primary"\n"2026-07-01","3"\n',
    )
    with pytest.raises(PipelineError, match="értelmezhetetlen sor"):
        parse(bad)


def test_file_without_daily_rows_raises(tmp_path):
    empty = _write(
        tmp_path / "Ures.csv", 'sep=,\n"Facebook-felkeresések"\n"Dátum","Primary"\n'
    )
    with pytest.raises(PipelineError, match="egyetlen napi sort sem"):
        parse(empty)


def test_override_can_be_keyed_by_file_name(tmp_path):
    """Két csatorna, egy csempenév — a névre kulcsolt override kevés.

    A Mammutnál a `Megtekintések` csempe mindkét csatornán ugyanígy hívják.
    Egyetlen csempenév-kulccsal mindkét fájl ugyanarra a csatornára került
    volna: az egyik görbe csendben a másik alá.
    """
    fb = _write(tmp_path / "Megtekintések.csv", 'sep=,\n"Megtekintések"\n"Dátum","Primary"\n"2026-07-01T00:00:00","7"\n')
    ig = _write(tmp_path / "Megtekintések-2.csv", 'sep=,\n"Megtekintések"\n"Dátum","Primary"\n"2026-07-01T00:00:00","5"\n')
    overrides = {
        "Megtekintések.csv": ("facebook", "views"),
        "Megtekintések-2.csv": ("instagram", "views"),
    }
    assert parse(fb, overrides=overrides).payload.channel == "facebook"
    assert parse(ig, overrides=overrides).payload.channel == "instagram"


def test_file_name_override_wins_over_the_metric_name(tmp_path):
    both = _write(tmp_path / "Megtekintések-2.csv", 'sep=,\n"Megtekintések"\n"Dátum","Primary"\n"2026-07-01T00:00:00","5"\n')
    overrides = {
        "Megtekintések": ("facebook", "views"),
        "Megtekintések-2.csv": ("instagram", "views"),
    }
    assert parse(both, overrides=overrides).payload.channel == "instagram"


def test_ambiguous_metric_help_offers_the_file_name_key(tmp_path):
    odd = _write(tmp_path / "Megtekintések-2.csv", 'sep=,\n"Megtekintések"\n"Dátum","Primary"\n"2026-07-01T00:00:00","5"\n')
    with pytest.raises(UnknownSourceError, match="Megtekintések-2.csv"):
        parse(odd)


def test_legacy_impressions_metric_help_maps_to_views(tmp_path):
    old = _write(tmp_path / "Megjelenések.csv", 'sep=,\n"Megjelenések"\n"Dátum","Primary"\n"2026-07-01T00:00:00","5"\n')
    with pytest.raises(UnknownSourceError) as caught:
        parse(old)

    assert '["facebook", "views"]' in str(caught.value)


def test_parsed_daily_export_can_be_filtered_to_an_inclusive_subperiod(input_file):
    series = parse(input_file("Felkeresések.csv")).payload

    filtered = filter_daily(series, date(2026, 7, 10), date(2026, 7, 12))

    assert [day for day, _ in filtered.points] == [
        date(2026, 7, 10),
        date(2026, 7, 11),
        date(2026, 7, 12),
    ]
