import csv
from datetime import date

import pytest

from pipeline.detect import identify
from pipeline.errors import PipelineError
from pipeline.detect import scan
from pipeline.parsers import meta_ads, meta_content, meta_daily
from pipeline.textio import read_csv_rows


def test_spaced_headers_and_bomless_utf16_excel_csv_are_recognised(tmp_path):
    path = tmp_path / 'unknown.csv'
    text = '\nsep=;\n Kampány neve ; Eredmény jelzése ; Elérés ; Megjelenések ; Jelentés kezdete ; Jelentés vége ; Elköltött összeg (HUF) \nNyár;reach;1 200;2 300;2026-07-01;2026-07-31;1 234,50\n'
    path.write_bytes(text.encode('utf-16-le'))
    assert identify(path).kind == 'meta_ads'
    row = meta_ads.parse(path).payload.campaigns[0]
    assert (row.reach, row.impressions, row.spend) == (1200, 2300, 1234.5)


@pytest.mark.parametrize('value', ['hibás', 'NaN', 'Infinity'])
def test_invalid_ads_numbers_never_become_zero(tmp_path, value):
    path = tmp_path / 'ads.csv'
    path.write_text('Kampány neve,Eredmény jelzése,Elérés,Megjelenések,Jelentés kezdete,Jelentés vége,Elköltött összeg (HUF)\n'
                    f'Nyár,reach,100,200,2026-07-01,2026-07-31,{value}\n', encoding='utf-8')
    with pytest.raises(PipelineError, match='Elköltött összeg'):
        meta_ads.parse(path)


def test_content_iso_date_and_localised_counts(tmp_path):
    path = tmp_path / 'content.csv'
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['Bejegyzésazonosító', 'Elérés', 'Megtekintések', 'Állandó hivatkozás', 'Közzététel időpontja', 'Kedvelések'])
        writer.writerow(['200', '1.234', '2,345', 'https://instagram.com/p/test/', '2026-07-15T11:30:00', '34'])
    post = meta_content.parse(path).payload[0]
    assert (post.reach, post.views, post.published) == (1234, 2345, date(2026, 7, 15))


def test_semicolon_daily_export_uses_declared_separator(tmp_path):
    path = tmp_path / 'daily.csv'
    path.write_text('sep=;\n"Instagram-követések"\n"Dátum";"Primary"\n"2026-07-01T00:00:00";"1 234"\n', encoding='utf-8')
    assert meta_daily.parse(path).payload.total == 1234


@pytest.mark.parametrize('text', ['Név,Név\nA,B\n', 'Név,Érték\nA,1,elveszne\n'])
def test_ambiguous_csv_structure_is_not_silently_truncated(tmp_path, text):
    path = tmp_path / 'bad.csv'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(PipelineError):
        read_csv_rows(path)


def test_generic_daily_parser_agrees_with_channel_detection(tmp_path):
    path = tmp_path / 'Facebook-Felkeresések.csv'
    path.write_text('sep=;\n"Felkeresések"\n"Dátum";"Primary"\n"2026-07-01";"3"\n', encoding='utf-8')
    parsed = meta_daily.parse(path)
    assert (parsed.payload.channel, parsed.payload.field, parsed.payload.total) == ('facebook', 'visits', 3)


def test_equal_daily_values_on_different_channels_are_not_duplicates(tmp_path):
    for channel in ('Facebook', 'Instagram'):
        (tmp_path / f'{channel}-Felkeresések.csv').write_text('sep=;\n"Felkeresések"\n"Dátum";"Primary"\n"2026-07-01";"3"\n', encoding='utf-8')
    assert [source.kind for source in scan(tmp_path)] == ['meta_daily', 'meta_daily']
