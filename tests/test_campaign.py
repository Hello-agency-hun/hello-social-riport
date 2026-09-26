"""A kampányriport: egy kiválasztott kampány a saját időszakára.

A minta egy két hónapos toborzási kampány heti bontású Ads-exporttal: két
hirdetéssorozat (Budapest, Szeged), mellette egy nem odatartozó kampány, és
napi csempék, amelyek a kampány előtti ugyanolyan hosszú időszakot is lefedik.
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from pipeline import campaign as campaign_mod
from pipeline.build import build
from pipeline.checklist import render as checklist
from pipeline.cli import main
from pipeline.errors import MissingConfigError, NarrativeError
from pipeline.narrative import resolve
from pipeline.render import render
from pipeline.schema import Campaign, DailySeries

START = date(2026, 6, 1)
WEEKS = 8
END = START + timedelta(days=7 * WEEKS - 1)  # 2026-07-26

HEADER = (
    "Jelentés kezdete,Jelentés vége,Kampány neve,Kampány teljesítése,Eredmények,"
    "Eredmény jelzése,Elérés,Gyakoriság,Elköltött összeg (HUF),Vége,Kezdés,"
    "Megjelenések,Hivatkozáskattintások\n"
)


def _ads_rows() -> str:
    rows = []
    for week in range(WEEKS):
        first = START + timedelta(days=7 * week)
        last = first + timedelta(days=6)
        # Budapest: végig fut, a kattintási arány hétről hétre csökken.
        rows.append(
            f"{first},{last},Toborzás_Budapest,completed,{250 - 8 * week},"
            f"actions:omni_landing_page_view,12000,1.7,{10000 + 1000 * week},"
            f"2026-07-26,2026-06-01,20000,{300 - 10 * week}"
        )
        if week >= 2:
            rows.append(
                f"{first},{last},TOBORZAS_Szeged,active,120,"
                "actions:omni_landing_page_view,6000,1.5,6000,folyamatban,2026-06-15,"
                "9000,150"
            )
    rows.append(
        f"{START},{END},Nyári menü,completed,900,reach,40000,1.2,50000,2026-07-26,"
        "2026-06-01,48000,400"
    )
    return HEADER + "\n".join(rows) + "\n"


def _daily_tile() -> str:
    first = START - timedelta(days=7 * WEEKS)
    lines = ['sep=,', '"Facebook-felkeresések"', '"Dátum","Primary"']
    day = first
    while day <= END:
        value = 15 if day >= START else 10
        lines.append(f'"{day.isoformat()}T00:00:00","{value}"')
        day += timedelta(days=1)
    return "\n".join(lines) + "\n"


CONFIG = """client:
  name: "Teszt Kft."
  fb_page_id: "123"

report:
  variant: campaign
  language: {language}

campaign:
  title: "Nyári toborzás"
  goal: "Jelentkezések a karrieroldalon"
  match: ["toborzas"]
  reach: 30000
"""


@pytest.fixture
def project(tmp_path):
    directory = tmp_path / "teszt" / "2026-07-toborzas"
    (directory / "input").mkdir(parents=True)
    (directory / "input" / "kampanyok.csv").write_text(_ads_rows(), encoding="utf-8")
    (directory / "input" / "Felkeresések.csv").write_text(_daily_tile(), encoding="utf-8")
    (directory / "client.yaml").write_text(CONFIG.format(language="hu"), encoding="utf-8")
    return directory


@pytest.fixture
def data(project):
    return build(project, "2026-07")


def test_only_the_matching_campaigns_count(data):
    """A „toborzas” minta ékezet és kisbetű nélkül is megtalálja a
    „Toborzás_Budapest” és a „TOBORZAS_Szeged” sort — a menüs kampány kimarad."""
    block = data["campaign"]
    assert {row["name"] for row in block["campaigns"]} == {
        "Toborzás_Budapest",
        "TOBORZAS_Szeged",
    }
    assert block["outside"] == {"campaigns": 1, "spend": 50000.0}
    assert data["paid"]["spend"] == block["totals"]["spend"]
    assert data["meta"]["variant"] == "campaign"


def test_the_period_is_the_campaigns_own(data):
    """Kézi dátum nélkül az Ads-export lekérési ablaka — nem a napi csempéké,
    amelyek a kampány előtti időszakot is lefedik."""
    assert (data["meta"]["measurement_start"], data["meta"]["measurement_end"]) == (
        "2026-06-01",
        "2026-07-26",
    )
    assert data["campaign"]["days"] == 56


def test_weekly_rows_merge_into_campaigns_without_adding_reach(data):
    """Aki két héten is látta a hirdetést, egy ember: a heti elérések összege
    nem a kampány elérése."""
    budapest = next(
        row for row in data["campaign"]["campaigns"] if row["name"] == "Toborzás_Budapest"
    )
    assert budapest["spend"] == sum(10000 + 1000 * week for week in range(WEEKS))
    assert budapest["impressions"] == 20000 * WEEKS
    assert budapest["reach"] is None
    assert budapest["frequency"] is None


def test_the_deduplicated_reach_comes_from_ads_manager(data):
    totals = data["campaign"]["totals"]
    assert totals["reach"] == 30000
    assert totals["reach_source"] == "ads_manager"
    assert totals["frequency"] == round(totals["impressions"] / 30000, 2)
    assert data["obtainable"] == []


def test_without_ads_manager_reach_several_campaigns_ask_for_it(project):
    config = (project / "client.yaml").read_text(encoding="utf-8")
    (project / "client.yaml").write_text(config.replace("  reach: 30000\n", ""), encoding="utf-8")
    data = build(project, "2026-07")
    assert data["campaign"]["totals"]["reach"] is None
    assert [item["key"] for item in data["obtainable"]] == ["campaign.reach"]


def test_the_funnel_ratios(data):
    totals = data["campaign"]["totals"]
    assert totals["ctr"] == round(totals["link_clicks"] / totals["impressions"], 4)
    assert totals["cpc"] == round(totals["spend"] / totals["link_clicks"], 2)
    assert totals["cpm"] == round(totals["spend"] * 1000 / totals["impressions"], 2)
    primary = data["campaign"]["primary"]
    assert primary["result_type"] == "actions:omni_landing_page_view"
    assert primary["results"] == sum(250 - 8 * week for week in range(WEEKS)) + 120 * 6
    assert primary["results_per_click"] == round(primary["results"] / totals["link_clicks"], 4)


def test_the_cheapest_result_is_named(data):
    best = data["campaign"]["best"]
    rows = data["campaign"]["campaigns"]
    assert best["cost_per_result"] == min(row["cost_per_result"] for row in rows)


def test_the_timeline_is_weekly_and_shows_click_fatigue(data):
    timeline = data["campaign"]["timeline"]
    assert timeline["granularity"] == "week"
    assert len(timeline["points"]) == WEEKS
    ctr = [point["ctr"] for point in timeline["points"][2:]]
    assert ctr == sorted(ctr, reverse=True), "a kattintási arány hétről hétre csökken"


def test_spans_use_the_real_start_dates(data):
    spans = {span["name"]: span for span in data["campaign"]["spans"]}
    assert spans["TOBORZAS_Szeged"]["start"] == "2026-06-15"
    assert spans["TOBORZAS_Szeged"]["ongoing"] is True


def test_the_page_movement_is_compared_with_the_period_before(data):
    lift = data["campaign"]["lift"]
    assert (lift["baseline_start"], lift["baseline_end"]) == ("2026-04-06", "2026-05-31")
    visits = lift["channels"]["facebook"]["visits"]
    assert (visits["before"], visits["during"], visits["pct"]) == (560, 840, 50.0)


def test_no_lift_when_the_tiles_do_not_cover_the_period_before():
    series = [
        DailySeries(
            "facebook", "visits", "Felkeresések",
            [(START + timedelta(days=offset), 5) for offset in range(56)],
        )
    ]
    assert campaign_mod.lift(series, START, END) == {}


def test_a_missing_selection_lists_what_is_in_the_export():
    campaigns = [Campaign(name="Toborzás_Budapest", spend=10.0), Campaign(name="Menü", spend=5.0)]
    with pytest.raises(MissingConfigError) as caught:
        campaign_mod.select(campaigns, {})
    assert "Toborzás_Budapest" in str(caught.value)
    assert "campaign:" in str(caught.value)
    with pytest.raises(MissingConfigError, match="egyetlen kampányra sem illik"):
        campaign_mod.select(campaigns, {"title": "x", "match": ["nincs ilyen"]})


def test_reach_campaigns_are_priced_per_thousand():
    """Elérésnél egy eredmény fillérekbe kerül; a Meta is ezerre vetít."""
    assert campaign_mod.cost_per_result(50.0, 100000, "reach") == 0.5
    assert campaign_mod.cost_per_result(50.0, 100, "actions:link_click") == 0.5


def test_the_campaign_report_renders_every_section(data, tmp_path):
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    assert "Nyári toborzás" in html
    assert "2026. június 1. – július 26." in html
    assert "Jelentkezések a karrieroldalon" in html
    assert "hetente" in html, "az idővonal oldal"
    assert html.count('class="chart"') >= 5, "négy idővonal-görbe és a futási sáv"
    assert "Mozdult-e az oldal a kampány alatt?" in html
    assert "+280" in html
    assert "legkedvezőbb eredményár" in html
    assert "a kattintók ennyien értek el az oldalra" in html
    # A havi riport fogalmai itt nem jelennek meg.
    assert "boost szorzója" not in html and "Változás az előző hónaphoz" not in html


def test_the_campaign_report_speaks_english(project, tmp_path):
    (project / "client.yaml").write_text(CONFIG.format(language="en"), encoding="utf-8")
    html = render(build(project, "2026-07"), cache_dir=tmp_path, fetcher=lambda url: b"")
    assert "1 June – 26 July 2026" in html
    assert "What the campaign delivered" in html
    body = re.sub(r"<(style|script)>.*?</\1>", "", html, flags=re.S)
    for phrase in ("hetente", "Mit hozott", "Előtte", "nap<"):
        assert phrase not in body, phrase


def test_narrative_can_reference_the_campaign(data):
    assert resolve("{campaign.totals.spend|money}", data).endswith("Ft")
    assert resolve("{campaign.primary.results}", data)
    with pytest.raises(NarrativeError, match="nem számolható"):
        resolve("{campaign.best.reach}", data)


def test_the_validate_map_names_the_selection(project, capsys):
    assert main([str(project), "--period", "2026-07", "--validate"]) == 0
    out = capsys.readouterr().out
    assert "„Nyári toborzás” — 2 kampány" in out
    assert "Kimaradt: 1 kampány" in out
    assert "Idővonal        8 pont (week)" in out
    assert "facebook/visits" in out


def test_the_validate_map_reads_like_the_report(project, capsys):
    """A kiválasztást a menedzserrel kell jóváhagyatni, tehát ő is olvassa:
    „144 000 Ft” és „Érkezésioldal-megtekintés”, nem „144000.00 HUF” és
    nyers Meta-kulcs. Az üresen maradt szakaszok sem hagynak hat üres sort."""
    main([str(project), "--period", "2026-07", "--validate"])
    out = capsys.readouterr().out
    assert "2 kampány, 144\u00a0000 Ft" in out
    assert "Kimaradt: 1 kampány, 50\u00a0000 Ft" in out
    assert "× Érkezésioldal-megtekintés" in out
    assert "\n\n\n" not in out
    assert "ZoomSphere      0 tartalom\n" in out, "nincs lógó gondolatjel"


def test_a_time_broken_down_export_counts_campaigns_not_rows(project, capsys):
    """Heti bontásnál egy kampány hetente külön sorban jön. A „15 kampány”
    félrevezetett: három kampány van, tizenöt sorban."""
    main([str(project), "--period", "2026-07", "--validate"])
    out = capsys.readouterr().out
    assert "3 kampány (0 boost) · 15 sor, idő szerint bontva, HUF" in out


def test_two_campaigns_with_one_name_are_not_a_breakdown(project, capsys):
    """Ugyanazt a posztot kétszer hirdetve két azonos nevű kampány jön,
    ugyanarra a lekérési ablakra. Ez két kampány, nem idő szerinti bontás."""
    (project / "input" / "kampanyok.csv").write_text(
        HEADER
        + f"{START},{END},Toborzás_Budapest,completed,100,"
        "actions:omni_landing_page_view,5000,1.5,10000,2026-07-26,2026-06-01,8000,120\n"
        + f"{START},{END},Toborzás_Budapest,completed,80,"
        "actions:omni_landing_page_view,4000,1.5,8000,2026-07-26,2026-06-15,6000,90\n",
        encoding="utf-8",
    )
    main([str(project), "--period", "2026-07", "--validate"])
    out = capsys.readouterr().out
    assert "2 kampány (0 boost), HUF" in out
    assert "idő szerint bontva" not in out


def test_a_left_placeholder_never_reaches_the_cover(project):
    """A vázból bennmaradt „<…>” nincs megadva: a kötelező cím hiánya megállít,
    az opcionális cél pedig kimarad — a helyőrző nem kerül az ügyfél elé."""
    config = CONFIG.format(language="hu")
    (project / "client.yaml").write_text(
        config.replace('"Nyári toborzás"', '"<a kampány neve a címlapon>"'),
        encoding="utf-8",
    )
    with pytest.raises(MissingConfigError, match="melyik kampányról szól"):
        build(project, "2026-07")

    (project / "client.yaml").write_text(
        config.replace('"Jelentkezések a karrieroldalon"', '"<a kampány célja egy mondatban>"'),
        encoding="utf-8",
    )
    assert build(project, "2026-07")["campaign"]["goal"] == ""


def test_a_campaign_folder_without_config_gets_a_campaign_skeleton(project):
    """Kampánymappában a hiányzó client.yaml helyett kampányváz jár: a havi
    váz követőszámot kért, ami ide nem kell, a kampány kiválasztása pedig
    kimaradt belőle."""
    (project / "client.yaml").unlink()
    with pytest.raises(MissingConfigError) as caught:
        build(project, "2026-07", "2026-06-01", "2026-07-26", variant="campaign")
    message = str(caught.value)
    assert "variant: campaign" in message
    assert "measurement_start: 2026-06-01" in message
    assert "campaign:\n  title:" in message
    assert "followers:" not in message


def test_the_checklist_is_about_the_campaign():
    text = checklist({"fb_page_id": "1"}, "clients/teszt/2026-07-toborzas", variant="campaign")
    assert "Kampányriport" in text
    assert "Bontás → Idő → Hét" in text
    assert "campaign.reach" in text
    assert "előtte lévő, ugyanolyan hosszú időszakra" in text


def test_the_checklist_yaml_is_complete_and_safe_to_paste():
    """A megadott dátumok bekerülnek, az opcionális mezők pedig kommentként
    állnak: ha a kitöltésük elmarad, nem kerül helyőrző a riportba."""
    text = checklist(
        {"fb_page_id": "1"},
        "clients/teszt/2026-07-toborzas",
        measurement_start="2026-06-01",
        measurement_end="2026-07-26",
        variant="campaign",
    )
    assert "    measurement_start: 2026-06-01" in text
    assert "    measurement_end: 2026-07-26" in text
    for optional in ("goal", "post_match", "reach"):
        assert f"    # {optional}:" in text


def test_the_monthly_report_is_untouched(fixture_dir, tmp_path):
    """A kampányváltozat nem változtat a havi riportadaton: nincs `campaign`
    kulcs, és a golden file ugyanaz marad (lásd test_cli)."""
    data = build(fixture_dir, "2026-07")
    assert "campaign" not in data
