import json
import io

import pytest
from PIL import Image

from pipeline.campaign import build, discover
from pipeline.campaign_cli import main
from pipeline.campaign_render import render_campaign
from pipeline.errors import PipelineError


def _project(tmp_path, ads_windows):
    directory = tmp_path / "campaign"
    inputs = directory / "input"
    inputs.mkdir(parents=True)
    (directory / "campaign.yaml").write_text(
        "campaign:\n"
        "  title: Back to School\n"
        "  start: '2026-08-01'\n"
        "  end: '2026-09-30'\n"
        "  variant: full\n"
        "  ads: [BTS Meta]\n"
        "  posts: ['facebook:200']\n"
        "  kpis:\n"
        "    - label: Regisztráció\n"
        "      target: '500'\n"
        "      actual: '420'\n",
        encoding="utf-8",
    )
    for index, (start, end, spend) in enumerate(ads_windows, 1):
        (inputs / f"ads-{index}.csv").write_text(
            "Kampány neve,Eredmény jelzése,Elérés,Megjelenések,Jelentés kezdete,"
            "Jelentés vége,Elköltött összeg (HUF),Hivatkozáskattintások\n"
            f"BTS Meta,reach,100,200,{start},{end},{spend},5\n"
            f"Nem ide tartozik,reach,999,999,{start},{end},999,99\n",
            encoding="utf-8",
        )
    (inputs / "scheduler.csv").write_text(
        "Datetime,PostType,FacebookPostIDs,InstagramPostIDs,FacebookSources,"
        "FacebookMessage,FacebookPublicPermalinks\n"
        '"15.08.2026 - 11:00 AM",image,100_200,,"Mammut (oldal)",Iskolakezdés,https://facebook.com/200\n',
        encoding="utf-8",
    )
    return directory


def test_multimonth_campaign_has_cumulative_and_monthly_metrics_without_summing_reach(tmp_path):
    path = _project(tmp_path, [("2026-08-01", "2026-08-31", 100),
                              ("2026-09-01", "2026-09-30", 300)])
    candidates = discover(path)
    assert {item["name"] for item in candidates["ads"]} == {"BTS Meta", "Nem ide tartozik"}
    assert candidates["posts"][0]["key"] == "facebook:200"

    result = build(path)
    assert result["summary"]["spend"] == 400
    assert result["summary"]["impressions"] == 400
    assert result["summary"]["reach"] is None
    assert result["summary"]["accuracy"] == "export_window"
    assert result["monthly"]["2026-08"]["spend"] == 100
    assert result["monthly"]["2026-09"]["spend"] == 300
    assert result["monthly"]["2026-08"]["posts"] == 1
    assert result["kpis"][0]["actual"] == "420"
    assert result["posts"][0]["reach"] is None
    assert "ismeretlen, nem nulla" in " ".join(result["warnings"])
    json.dumps(result, ensure_ascii=False)


def test_cross_month_ads_go_to_unallocated_not_an_arbitrary_month(tmp_path):
    path = _project(tmp_path, [("2026-08-20", "2026-09-10", 240)])
    result = build(path)
    assert result["summary"]["spend"] == 240
    assert result["monthly"]["2026-08"]["spend"] == 0
    assert result["monthly"]["2026-08"]["ads_measured"] is False
    assert result["missing_ad_months"] == ["2026-08", "2026-09"]
    assert len(result["unallocated_ads"]) == 1


def test_overlapping_ads_exports_are_rejected(tmp_path):
    path = _project(tmp_path, [("2026-08-01", "2026-08-20", 100),
                              ("2026-08-15", "2026-08-31", 200)])
    with pytest.raises(PipelineError, match="Átfedő"):
        build(path)


def test_selected_missing_post_is_rejected(tmp_path):
    path = _project(tmp_path, [("2026-08-01", "2026-08-31", 100)])
    config = path / "campaign.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("facebook:200", "instagram:404"), encoding="utf-8")
    with pytest.raises(PipelineError, match="instagram:404"):
        build(path)


def test_campaign_cli_discovers_and_writes_json(tmp_path, capsys):
    path = _project(tmp_path, [("2026-08-01", "2026-08-31", 100)])
    assert main([str(path), "--discover"]) == 0
    assert "facebook:200" in capsys.readouterr().out
    target = tmp_path / "result.json"
    html = tmp_path / "Riport.html"
    assert main([str(path), "--out", str(target), "--html", str(html), "--offline"]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["meta"]["title"] == "Back to School"
    markup = html.read_text(encoding="utf-8")
    assert "Back to School" in markup and "A manager által megadott célok" in markup
    assert "data:image/svg+xml;base64," in markup
    assert markup.count('class="page') >= 6


def test_narrative_rejects_literal_digits_without_damaging_previous_report(tmp_path, capsys):
    path = _project(tmp_path, [("2026-08-01", "2026-08-31", 100)])
    (path / "narrative.json").write_text('{"executive_summary": "1 rossz szám"}', encoding="utf-8")
    assert main([str(path), "--offline"]) == 1
    assert "kézzel írt szám" in capsys.readouterr().err
    assert not (path / "Riport.html").exists()


def test_selected_post_creative_is_embedded_in_standalone_html(tmp_path):
    path = _project(tmp_path, [("2026-08-01", "2026-08-31", 100)])
    scheduler = path / "input" / "scheduler.csv"
    text = scheduler.read_text(encoding="utf-8")
    scheduler.write_text(
        text.replace("FacebookPublicPermalinks", "FacebookPublicPermalinks,FacebookImages")
        .replace("https://facebook.com/200", "https://facebook.com/200,https://example.test/post.png"),
        encoding="utf-8",
    )
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "red").save(buffer, format="PNG")
    html = render_campaign(build(path), cache_dir=tmp_path / "image-cache", fetcher=lambda url: buffer.getvalue())
    assert "data:image/jpeg;base64," in html
    assert "data:image/svg+xml;base64," not in html
