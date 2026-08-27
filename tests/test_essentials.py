"""Az Essentials riport: rövidebb, tíz dia, hagyományosabb rangsorral.

Egy másik social media manager kérte. A számokat ugyanaz a pipeline adja —
csak kevesebb kerül belőle a riportba, és a legjobb posztok sorrendje nem a
rezonancia-index, hanem az interakciók száma.
"""

from datetime import date
from pathlib import Path

from pipeline.build import _essentials_missing
from pipeline.kpi import audience, engagement_breakdown
from pipeline.render import _essentials_posts, _template_name
from pipeline.schema import DailySeries, Post


def _post(**kwargs) -> Post:
    base = dict(
        channel="instagram",
        post_id="1",
        published=None,
        organic_measured=True,
    )
    base.update(kwargs)
    return Post(**base)


def test_engagement_breaks_down_by_type():
    posts = [
        _post(reactions=10, comments=2, shares=3, saves=4),
        _post(post_id="2", reactions=5, comments=1, shares=0, saves=1),
    ]
    out = engagement_breakdown(posts)
    assert out["reactions"] == 15
    assert out["comments"] == 3
    assert out["shares"] == 3
    assert out["saves"] == 5
    assert out["total"] == 26
    assert out["posts_counted"] == 2


def test_engagement_counts_only_measured_posts():
    """A ZoomSphere-ből ismert, de nem mért posztnak nincs interakciószáma.

    Nullaként beszámítani azt jelentené, hogy „mértük, és nem reagált rá
    senki" — pedig nem mértük.
    """
    posts = [
        _post(reactions=10),
        _post(post_id="2", organic_measured=False),
    ]
    assert engagement_breakdown(posts)["posts_counted"] == 1


def test_essentials_ranks_by_interactions_not_reach():
    """A hagyományosabb sorrend nem az elérés: azt a költés dönti el.

    A manager mindkét számot kéri a kártyán, de a rangsort az interakció adja.
    """
    big_reach = _post(post_id="nagy", reach=10000, reactions=1)
    engaging = _post(post_id="eros", reach=200, reactions=50, comments=5)
    selected = _essentials_posts([big_reach.__dict__, engaging.__dict__])
    assert [p["post_id"] for p in selected] == ["eros", "nagy"]


def test_essentials_shows_three_posts():
    posts = [_post(post_id=str(i), reactions=i).__dict__ for i in range(9)]
    assert len(_essentials_posts(posts)) == 3


def test_template_follows_the_variant():
    assert _template_name("essentials") == "report-essentials.html.j2"
    assert _template_name("full") == "report.html.j2"
    assert _template_name(None) == "report.html.j2"
    assert _template_name("ismeretlen") == "report.html.j2"


def test_essentials_names_every_missing_traditional_metric():
    config = {"report": {"variant": "essentials"}}
    client = {"fb_page_id": "123"}
    series = [
        DailySeries(
            channel="facebook",
            field="views",
            metric="Megtekintések",
            points=[(date(2026, 7, 1), 10)],
        )
    ]

    missing = _essentials_missing(config, client, {"facebook": "content.csv"}, series)

    assert any("Facebook" in item and "Interakciók" in item for item in missing)
    assert any("Facebook" in item and "Felkeresések" in item for item in missing)
    assert any("Facebook" in item and "Hivatkozáskattintások" in item for item in missing)
    assert any("Facebook" in item and "Új követők" in item for item in missing)
    assert not any("Megjelenések" in item for item in missing)


def test_full_report_does_not_gain_essentials_only_blockers():
    assert _essentials_missing(
        {"report": {"variant": "full"}},
        {"fb_page_id": "123"},
        {},
        [],
    ) == []


def test_previous_and_current_followers_satisfy_growth_without_follows_tile():
    config = {
        "report": {"variant": "essentials"},
        "followers": {"facebook": 110},
    }
    client = {"fb_page_id": "123"}
    series = [
        DailySeries("facebook", field, field, [(date(2026, 7, 1), 1)])
        for field in ("views", "interactions", "visits", "link_clicks")
    ]
    previous = {"audience": {"facebook": {"followers": 100}}}

    missing = _essentials_missing(
        config,
        client,
        {"facebook": "content.csv"},
        series,
        previous=previous,
    )

    assert missing == []


def test_audience_growth_can_use_previous_follower_total():
    result = audience(
        {"facebook": {"totals": {}}},
        {"facebook": 110},
        previous_audience={"facebook": {"followers": 100}},
    )

    assert result["facebook"]["new_followers"] == 10
    assert result["facebook"]["growth"] == 0.1


def test_essentials_template_keeps_zero_saves_visible():
    source = (Path(__file__).parents[1] / "templates" / "report-essentials.html.j2").read_text(
        encoding="utf-8"
    )

    # A mért nullát nem rejtjük el — az adat, nem hiány. A `{% if post.saves %}`
    # viszont pont ezt tenné: a nullát hamisnak veszi.
    assert "{% if post.saves %}" not in source
    assert "{% if block.engagement.saves %}" not in source
    # A NEM mért mentést viszont el kell hagyni: a Facebook exportjában nincs is
    # ilyen oszlop, ott a nulla olyat állítana, amit sosem mértünk.
    assert "{% if post.saves is not none %}" in source
    assert "{% if block.engagement.saves_measured %}" in source
    assert "t.essentials_impressions" in source


def test_follower_stock_and_reach_get_a_month_over_month_change():
    """„Nőttünk vagy csökkentünk?" — az ügyfél ezt a két számot nézi elsőként.

    Egyik sem a napi csempékből jön, ezért eddig kimaradt az összehasonlításból.
    Az előző havi riportban viszont mindkettő ott van, tehát nincs mit kitalálni.
    """
    from pipeline.build import build
    import json
    import shutil
    import tempfile
    from pathlib import Path

    fixture = Path(__file__).resolve().parent / "fixtures" / "larus-2026-07"
    work = Path(tempfile.mkdtemp())
    for item in fixture.iterdir():
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, work / item.name)
    (work / "previous.json").write_text(
        json.dumps(
            {
                "meta": {"period": "2026-06"},
                "channels": {},
                "audience": {"facebook": {"followers": 4000, "monthly_reach": 100000}},
            }
        ),
        encoding="utf-8",
    )
    (work / "client.yaml").write_text(
        (work / "client.yaml").read_text(encoding="utf-8").replace(
            "report:", "monthly_reach:\n  facebook: 120000\n\nreport:"
        ),
        encoding="utf-8",
    )

    data = build(work, "2026-07")
    facebook = data["comparison"]["facebook"]
    assert facebook["followers"]["before"] == 4000
    assert facebook["monthly_reach"]["before"] == 100000
    assert facebook["monthly_reach"]["diff"] == 20000


def test_variant_flag_overrides_the_client_yaml(tmp_path):
    """Ugyanabból az adatból két riport: a menedzsernek a teljes, az ügyfélnek a rövid.

    A `client.yaml` átírása két futás között azt jelentené, hogy a projekt
    beállítása csendben elcsúszik attól, ami az utolsó riportban van.
    """
    import shutil
    from pathlib import Path

    from pipeline.build import build

    fixture = Path(__file__).resolve().parent / "fixtures" / "larus-2026-07"
    for item in fixture.iterdir():
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, tmp_path / item.name)

    assert build(tmp_path, "2026-07")["meta"]["variant"] == "full"

def test_the_second_variant_never_kills_the_first(tmp_path, capsys):
    """A második riport kiegészítés, nem szállítmány.

    A Larus adata nem elégíti ki az Essentials követelményeit — ettől még a
    teljes riportnak el kell készülnie. Korábban a második build hibája az
    egész futást megölte, tehát egy opcionális másolat vitte volna magával a
    kész fő riportot.
    """
    import shutil
    from pathlib import Path

    from pipeline.cli import main

    fixture = Path(__file__).resolve().parent / "fixtures" / "larus-2026-07"
    for item in fixture.iterdir():
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, tmp_path / item.name)
    config = (tmp_path / "client.yaml").read_text(encoding="utf-8")
    (tmp_path / "client.yaml").write_text(
        config.replace("report:", "report:\n  also_variant: essentials"), encoding="utf-8"
    )

    assert main([str(tmp_path), "--period", "2026-07", "--offline", "--allow-fixture"]) == 0
    assert (tmp_path / "Riport.html").exists()
    assert not (tmp_path / "Riport-essentials.html").exists()
    # És megmondja, min múlt — a néma kihagyás rosszabb, mint a hiba.
    assert "Instagram Tartalom CSV" in capsys.readouterr().err
