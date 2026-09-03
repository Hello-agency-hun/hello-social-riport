from datetime import date

import pytest

from pipeline.detect import identify
from pipeline.parsers.meta_ads import detect_currency, parse


ADS_HEADER = [
    "Kampány neve",
    "Eredmény jelzése",
    "Elérés",
    "Megjelenések",
    "Jelentés kezdete",
    "Jelentés vége",
    "Elköltött összeg (HUF)",
]
ADS_ROW = ["Nyári kampány", "reach", 123, 456, "2026-07-01", "2026-07-31", 789]


def test_currency_is_read_from_the_header():
    assert detect_currency(["Eredmények", "Elköltött összeg (EUR)"]) == "EUR"
    assert detect_currency(["Elköltött összeg (HUF)"]) == "HUF"


def test_windows_1250_ads_export_is_parsed_without_manual_conversion(tmp_path):
    path = tmp_path / "kampanyok.csv"
    csv_text = (
        "Kampány neve,Eredmény jelzése,Elérés,Megjelenések,Jelentés kezdete,"
        "Jelentés vége,Elköltött összeg (HUF)\n"
        "Nyári kampány,reach,123,456,2026-07-01,2026-07-31,789\n"
    )
    path.write_bytes(csv_text.encode("cp1250"))

    source = parse(path)

    assert source.payload.currency == "HUF"
    assert source.payload.campaigns[0].name == "Nyári kampány"
    assert source.payload.campaigns[0].reach == 123


def test_excel_semicolon_ads_export_is_parsed_without_manual_conversion(tmp_path):
    path = tmp_path / "kampanyok-pontosvesszo.csv"
    csv_text = (
        "sep=;\n"
        "Kampány neve;Eredmény jelzése;Elérés;Megjelenések;Jelentés kezdete;"
        "Jelentés vége;Elköltött összeg (HUF)\n"
        "Nyári kampány;reach;123;456;2026-07-01;2026-07-31;789\n"
    )
    path.write_bytes(csv_text.encode("cp1250"))

    source = parse(path)

    assert source.payload.campaigns[0].name == "Nyári kampány"
    assert source.payload.campaigns[0].impressions == 456


@pytest.mark.parametrize("name_column", ["Hirdetéssorozat neve", "Hirdetés neve"])
def test_ads_export_from_a_more_detailed_level_uses_its_available_name(tmp_path, name_column):
    path = tmp_path / "meta-reszletesebb-szint.csv"
    path.write_text(
        f"{name_column},Eredmény jelzése,Elérés,Megjelenések,Jelentés kezdete,"
        "Jelentés vége,Elköltött összeg (HUF)\n"
        "FUP bejegyzés,reach,123,456,2026-08-01,2026-08-31,789\n",
        encoding="utf-8",
    )

    assert identify(path).kind == "meta_ads"
    source = parse(path)

    assert source.payload.campaigns[0].name == "FUP bejegyzés"
    assert source.payload.source_level == ("adset" if name_column == "Hirdetéssorozat neve" else "ad")


@pytest.mark.parametrize("suffix", [".xls", ".xlsx"])
def test_textual_csv_is_parsed_even_when_excel_extension_was_used(tmp_path, suffix):
    """A kiterjesztés átnevezése nem teheti olvashatatlanná a jó CSV-t."""
    path = tmp_path / f"teljesen-rossz-nev{suffix}"
    path.write_text(
        ",".join(ADS_HEADER) + "\n" + ",".join(map(str, ADS_ROW)) + "\n",
        encoding="utf-8",
    )

    assert identify(path).kind == "meta_ads"
    assert parse(path).payload.campaigns[0].reach == 123


def test_real_xlsx_ads_export_is_identified_and_parsed_by_its_schema(tmp_path):
    """A valódi XLSX Meta Ads-exportot nem szabad CSV-vé mentésre visszadobni."""
    from openpyxl import Workbook

    path = tmp_path / "valami-fontos-de-rosszul-elnevezve.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(ADS_HEADER)
    sheet.append(ADS_ROW)
    workbook.save(path)

    assert identify(path).kind == "meta_ads"
    source = parse(path)
    assert source.period == (date(2026, 7, 1), date(2026, 7, 31))
    assert source.payload.campaigns[0].name == "Nyári kampány"


def test_real_legacy_xls_ads_export_is_identified_and_parsed_by_its_schema(tmp_path):
    """A bináris .xls is használható, ha a szükséges oszlopok felismerhetők."""
    import xlwt

    path = tmp_path / "ismeretlen-fajl.xls"
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("Meta Ads")
    for column, value in enumerate(ADS_HEADER):
        sheet.write(0, column, value)
    for column, value in enumerate(ADS_ROW):
        sheet.write(1, column, value)
    workbook.save(str(path))

    assert identify(path).kind == "meta_ads"
    assert parse(path).payload.campaigns[0].impressions == 456


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


def test_boost_prefix_is_found_after_a_client_prefix():
    """A Meta a boost nevét gyakran az ügyfél saját előtagja mögé teszi.

    A Mammut júliusi exportjában minden kampány `Mammut_Bejegyzés: …`
    alakban jött. Amíg a felismerés a sor elejéhez kötött, egyetlen boost sem
    azonosítódott — a hirdetett posztok csendben kimaradtak a rangsorból.
    """
    from pipeline.parsers.meta_ads import _boost_channel

    assert _boost_channel("Mammut_Bejegyzés: „Nyáron is irány a Mammut!”") == "facebook"
    assert _boost_channel("Mammut_Instagram-bejegyzés: Hangolódj a nyári…") == "instagram"
    assert _boost_channel("Bejegyzés: hagyományos alak") == "facebook"
    assert _boost_channel("Instagram-bejegyzés: hagyományos alak") == "instagram"


def test_always_on_campaigns_are_still_not_boosts():
    """A javítás nem teheti boosttá azt, ami nem az."""
    from pipeline.parsers.meta_ads import _boost_channel

    assert _boost_channel("Mammut_Always-on forgalomterelés") is None
    assert _boost_channel("Nyári kampány — bejegyzések helyett") is None


def test_campaign_state_uses_real_campaign_dates_and_report_window(tmp_path):
    path = tmp_path / "campaign-state.csv"
    path.write_text(
        "Kampány neve,Eredmény jelzése,Elérés,Megjelenések,Eredmények,"
        "Jelentés kezdete,Jelentés vége,Kezdés,Vége,Kampány teljesítése,"
        "Elköltött összeg (HUF)\n"
        "Nyári kampány,reach,123,456,42,2026-06-01,2026-07-31,"
        "2026-06-20,folyamatban,ACTIVE,789\n",
        encoding="utf-8",
    )

    campaign = parse(path).payload.campaigns[0]

    assert campaign.start_date == date(2026, 6, 20)
    assert campaign.end_date is None
    assert campaign.is_ongoing is True
    assert campaign.delivery_status == "active"
    assert campaign.report_start == date(2026, 6, 1)
    assert campaign.report_end == date(2026, 7, 31)


def test_report_start_is_never_reused_as_a_missing_campaign_start(tmp_path):
    path = tmp_path / "campaign-without-start.csv"
    path.write_text(
        "Kampány neve,Eredmény jelzése,Elérés,Megjelenések,"
        "Jelentés kezdete,Jelentés vége,Vége,Kampány teljesítése,"
        "Elköltött összeg (HUF)\n"
        "Nyári kampány,reach,123,456,2026-06-01,2026-07-31,"
        "2026-07-20,COMPLETED,789\n",
        encoding="utf-8",
    )

    campaign = parse(path).payload.campaigns[0]

    assert campaign.start_date is None
    assert campaign.end_date == date(2026, 7, 20)
    assert campaign.report_start == date(2026, 6, 1)
