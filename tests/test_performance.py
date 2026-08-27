import json
from pathlib import Path

from pipeline import performance

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)


def post(reach=1000, reactions=0, comments=0, shares=0, link_clicks=0, paid=None, **kw):
    return {
        "reach": reach,
        "reactions": reactions,
        "comments": comments,
        "shares": shares,
        "link_clicks": link_clicks,
        "paid": paid,
        "organic_measured": True,
        **kw,
    }


def test_a_share_counts_for_more_than_a_like():
    """Egy lájk egy koppintás; egy megosztás azt jelenti, hogy valaki a saját
    nevét adta hozzá a tartalomhoz a saját ismerőseinek."""
    assert performance.weighted_interactions(post(shares=1)) > (
        performance.weighted_interactions(post(reactions=1))
    )
    assert performance.weighted_interactions(post(comments=1)) > (
        performance.weighted_interactions(post(reactions=1))
    )


def test_link_clicks_are_deliberately_excluded():
    """Első nekifutásra benne volt, és a rangsor élére azonnal visszaült a
    legnagyobb hirdetés: a Tartalom export kattintás-oszlopa a FIZETETT
    kattintást is tartalmazza. Ezzel pont azt a torzítást engedtük volna
    vissza, ami miatt az egész pontozás készült."""
    assert "link_clicks" not in performance.WEIGHTS
    assert performance.weighted_interactions(post(link_clicks=5000)) == 0


def test_paid_reach_does_not_buy_a_better_score():
    """Ez az egész lényege: a boost elérést vesz, nem rezonanciát. Ha az
    emberek nem szóltak hozzá, az arány leesik."""
    small = post(reach=200, reactions=4)
    huge = post(reach=9000, reactions=4, paid={"spend": 16.0})
    scored = performance.score_posts([small, huge])

    assert scored[0]["score"]["resonance"] > scored[1]["score"]["resonance"]
    assert performance.ranked(scored)[0] is small


def test_a_post_without_measured_reach_is_not_scored_as_zero():
    """Nullát adni azt jelentené, hogy „mértük, és rossz volt” — pedig nem
    mértük. Az Instagram-posztok jellemzően ilyenek."""
    unmeasured = post(reach=0, organic_measured=False)
    assert performance.score_posts([unmeasured])[0]["score"] is None
    assert performance.ranked([unmeasured]) == []


def test_the_median_is_used_not_the_average():
    """Egyetlen erősen boostolt poszt az átlagot felhúzza, és onnantól
    mindenki alulteljesítőnek látszik."""
    posts = [post(reach=100, reactions=1) for _ in range(4)]
    posts.append(post(reach=100, reactions=90))
    scored = performance.score_posts(posts)

    # A négy szokásos poszt a mediánnal egyenlő, tehát 1,0× körül van
    assert scored[0]["score"]["vs_typical"] == 1.0
    # Átlaggal ez 0,2 körül lenne, és mind a négy gyengének látszana.


def test_both_cohorts_get_a_place_on_the_page():
    """A Mammut-próbán Facebookon mind a hat kártya organikus lett — pedig öt
    poszt kapott hirdetést. Az adat helyes volt, a bemutatás hamis: a
    Facebook-oldalra nézve úgy tűnt, egyetlen forint hirdetés sem ment ki."""
    strong_organic = [post(reach=100, reactions=30 + i) for i in range(9)]
    weak_boosted = [
        post(reach=5000, reactions=10 + i, paid={"spend": 12.0}) for i in range(5)
    ]
    scored = performance.score_posts(strong_organic + weak_boosted)

    chosen = performance.balanced(scored, limit=6)
    assert len(chosen) == 6
    assert any(p["score"]["boosted"] for p in chosen), "hirdetett poszt is kell"
    assert any(not p["score"]["boosted"] for p in chosen), "organikus is kell"


def test_a_single_cohort_still_fills_the_page():
    """Ha nincs hirdetett poszt, ne maradjon üres hely."""
    scored = performance.score_posts([post(reach=100, reactions=5 + i) for i in range(8)])
    assert len(performance.balanced(scored, limit=6)) == 6


def test_the_real_data_says_the_reach_leader_is_not_the_best_post():
    """A Larus júliusában a legnagyobb elérésű poszt (Séfünk ajánlata, 9 046)
    a látók 0,27%-át mozdította meg; a Gambas Pil-Pil az 5,55%-át."""
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    found = data["performance"]["facebook"]

    assert found["top_is_reach_leader"] is False
    assert "Gambas" in found["top"]["caption"]
    assert "Séfünk" in found["reach_leader"]["caption"]
    assert found["top"]["engagement_rate"] > found["reach_leader"]["engagement_rate"]


def test_the_best_unboosted_post_is_surfaced_for_the_narrative():
    """„Lehetnek olyan posztok is, amik magukhoz képest organikusan is nagyot
    mentek volna” — ez az a mező, ami ezt megmutatja."""
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    best = data["performance"]["facebook"]["best_unboosted"]

    assert best["boosted"] is False
    assert best["vs_typical"] >= 1.5
    assert data["performance"]["facebook"]["best_unboosted_beats_typical"] is True


def test_saves_sit_between_comments_and_shares_on_the_effort_ladder():
    """A mentés szándékosabb, mint egy hozzászólás, de nem adja hozzá a nevét.

    A létra sorrendje a lényeg: reakció < hozzászólás < mentés < megosztás.
    """
    from pipeline.performance import WEIGHTS, weighted_interactions

    assert WEIGHTS["reactions"] < WEIGHTS["comments"] < WEIGHTS["saves"] < WEIGHTS["shares"]
    post = {"reactions": 0, "comments": 0, "shares": 0, "saves": 2}
    assert weighted_interactions(post) == 2 * WEIGHTS["saves"]


def test_saved_posts_beat_merely_liked_ones():
    from pipeline.performance import weighted_interactions

    liked = {"reactions": 5, "comments": 0, "shares": 0, "saves": 0}
    saved = {"reactions": 0, "comments": 0, "shares": 0, "saves": 5}
    assert weighted_interactions(saved) > weighted_interactions(liked)
