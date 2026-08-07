"""Melyik poszt teljesített jól — és miért nem az elérés mondja meg.

Elérés szerint rangsorolni annyi, mint **költés szerint rangsorolni**. Amelyik
posztra a legtöbb pénz ment, az lesz elöl; ez tautológia, nem megállapítás. A
Larus júliusában a négy legnagyobb elérésű poszt pontosan az a négy volt,
amelyiket megtámogattuk — a rangsor semmi újat nem mondott.

Amit tudni akarunk: **azok közül, akik látták, hányan reagáltak rá.** Ez a
támogatást kiüti a képletből: ha a boost vett elérést, de az emberek nem
szóltak hozzá, az arány leesik.

## A súlyozás

A reakciók nem egyenértékűek. Egy lájk egy koppintás; egy komment szándékot
igényel; egy megosztás azt jelenti, hogy valaki a **saját nevét adta hozzá** a
tartalomhoz a saját ismerőseinek. Ezért:

    reakció 1 · hozzászólás 4 · megosztás 8

A pontos súlyok nem szentírás; a **sorrendjük** az, ami számít, és az iparági
gyakorlattal egyezik. A skála log-szerű, mert a ráfordított erőfeszítés is az.

**A hivatkozáskattintás szándékosan nincs benne.** Első nekifutásra kettes
súllyal beletettem, mert vendéglátásnál a foglalási szándék közelítése — és a
rangsor élére azonnal visszaült a legnagyobb hirdetés. A Tartalom export
kattintás-oszlopa ugyanis a **fizetett** kattintást is tartalmazza: a
séf-ajánlaton az ezerhez közeli kattintásból szinte mindet a hirdetés hozta.
Ezzel pontosan azt a torzítást engedtük volna vissza, ami miatt az egész
pontozás készült. A kattintás hirdetési eredmény; a fizetett szekcióban a
helye, nem a tartalmi rezonanciában.

## Önmagához képest — és a hasonlókhoz

A nyers arány még mindig félrevihet: egy kétszáz embert elért poszt könnyebben
produkál magas százalékot, mint egy tízezres. Ezért minden posztot egy
**medián** értékhez mérünk. Mediánt, nem átlagot: egyetlen kiugró poszt az
átlagot felhúzza, és onnantól mindenki alulteljesítőnek látszik.

**De nem a csatorna egészéhez mérünk, hanem a saját mezőnyéhez.** Ez a
tanulság a PETI-próbából jött: ott mindkét csatornán *minden* hirdetett poszt a
szerves posztok mögé került, és nem véletlenül. Egy boostolt poszt elérésében
benne van a fizetett terjesztés is — egy hidegebb közönség, amelyik
természetesen kevesebbet reagál. Ha az interakciót ezzel a nagyobb, kevertebb
nevezővel osztjuk, a hirdetett posztot **automatikusan büntetjük**. Almát
osztunk körtével, és a riportból úgy tűnik, mintha nem is hirdetnénk.

Ezért két mezőny van: a boostolt posztokat a boostoltakhoz, a szerveseket a
szervesekhez mérjük. Így a kérdés az lesz, ami érdekes: *a saját fajtájához
képest hogyan teljesített?*

Ha egy mezőnyben túl kevés poszt van ahhoz, hogy a mediánja jelentsen valamit
(`MIN_COHORT`), visszaesünk a csatorna egészére — egyetlen poszt mediánja
önmaga, abból nem lesz viszonyítási alap.
"""

from statistics import median

# Az erőfeszítés-létra. A sorrend a lényeg, nem a pontos érték.
WEIGHTS = {
    "reactions": 1,
    "comments": 4,
    "shares": 8,
}


def weighted_interactions(post: dict) -> int:
    return sum(int(post.get(key) or 0) * weight for key, weight in WEIGHTS.items())


def _resonance(post: dict) -> float | None:
    """Súlyozott interakció / elérés. `None`, ha nincs mért elérés."""
    reach = int(post.get("reach") or 0)
    if not post.get("organic_measured") or reach <= 0:
        return None
    return weighted_interactions(post) / reach


def _engagement_rate(post: dict) -> float | None:
    """A megszokott, súlyozatlan arány — hogy legyen egy ismerős szám is."""
    reach = int(post.get("reach") or 0)
    if not post.get("organic_measured") or reach <= 0:
        return None
    plain = sum(int(post.get(key) or 0) for key in ("reactions", "comments", "shares"))
    return plain / reach


# Ennyi poszt kell egy mezőnyhöz, hogy a mediánja jelentsen valamit.
MIN_COHORT = 3


def _cohort_medians(posts: list[dict]) -> dict[bool, float]:
    """Külön viszonyítási alap a boostolt és a szerves mezőnynek."""
    everything = [r for r in (_resonance(p) for p in posts) if r is not None]
    overall = median(everything) if everything else 0.0

    out = {}
    for boosted in (True, False):
        values = [
            r
            for r in (
                _resonance(p) for p in posts if bool(p.get("paid")) is boosted
            )
            if r is not None
        ]
        out[boosted] = median(values) if len(values) >= MIN_COHORT else overall
    return out


def score_posts(posts: list[dict]) -> list[dict]:
    """Minden posztra rátesz egy `score` blokkot. A listát nem rendezi át.

    A `score` `None` marad ott, ahol nincs mért elérés — az Instagram-posztok
    jellemzően ilyenek. Nullát adni helyette azt jelentené, hogy „mértük, és
    rossz volt", pedig nem mértük.
    """
    medians = _cohort_medians(posts)

    for post in posts:
        resonance = _resonance(post)
        if resonance is None:
            post["score"] = None
            continue
        boosted = bool(post.get("paid"))
        typical = medians[boosted]
        post["score"] = {
            "resonance": round(resonance, 5),
            "engagement_rate": round(_engagement_rate(post) or 0, 4),
            "weighted_interactions": weighted_interactions(post),
            # Hányszorosa a SAJÁT mezőnye szokásos teljesítményének.
            "vs_typical": round(resonance / typical, 2) if typical else None,
            "boosted": boosted,
        }
    return posts


def ranked(posts: list[dict]) -> list[dict]:
    """A pontozott posztok, legjobbtól lefelé. A pontozatlanok kimaradnak.

    A rendezés a mezőnyön belüli teljesítmény szerint megy, nem a nyers arány
    szerint — különben a boostolt posztok mindig hátraszorulnának, és a
    riportból úgy tűnne, mintha nem is hirdetnénk.
    """
    scored = [p for p in posts if p.get("score")]
    return sorted(scored, key=lambda p: -(p["score"]["vs_typical"] or 0))


def balanced(posts: list[dict], limit: int = 6) -> list[dict]:
    """A riportba kerülő posztok — mindkét mezőnyből.

    A `ranked` önmagában monokultúrát adhat, és a Mammut-próbán adott is:
    Facebookon mind a hat kártya organikus lett (pedig öt poszt kapott
    hirdetést), Instagramon mind a hat hirdetett (pedig kilenc organikus volt).
    Az ok kézenfekvő: ahol az egyik mezőny mediánja alacsony, ott annak a
    mezőnynek a tagjai kapnak nagy szorzót.

    Az adat így is helyes, a **bemutatás** viszont hamis: a Facebook-oldalra
    nézve úgy tűnt, egyetlen forint hirdetés sem ment ki — miközben az első
    oldalon ott a költés.

    Ezért a helyeket arányosan osztjuk a két mezőny között, de legalább egyet
    mindkettőnek adunk, ha van jelöltje. A sorrend a listán belül változatlanul
    teljesítmény szerint megy.
    """
    order = ranked(posts)
    if not order:
        return []

    boosted = [p for p in order if p["score"]["boosted"]]
    organic = [p for p in order if not p["score"]["boosted"]]
    if not boosted or not organic:
        return order[:limit]

    # Arányos elosztás, de mindkét mezőny kap legalább egy helyet.
    share = round(limit * len(boosted) / (len(boosted) + len(organic)))
    for_boosted = max(1, min(limit - 1, share))
    picked = boosted[:for_boosted] + organic[: limit - for_boosted]

    # Ha az egyik mezőnyből kevesebb jelölt volt, a maradékot a másik tölti fel.
    if len(picked) < limit:
        rest = [p for p in order if p not in picked]
        picked += rest[: limit - len(picked)]

    return sorted(picked, key=lambda p: -(p["score"]["vs_typical"] or 0))


def findings(posts: list[dict]) -> dict:
    """Amit a rangsorból érdemes elmondani — a narratívának.

    Ezek a mezők azért vannak a riportadatban, hogy a szöveg **hivatkozni**
    tudjon rájuk. A narratívába számot írni tilos; ami nincs itt, arról nem
    lehet állítást tenni.
    """
    order = ranked(posts)
    if not order:
        return {}

    best = order[0]
    by_reach = max(posts, key=lambda p: int(p.get("reach") or 0))
    unboosted = [p for p in order if not p.get("paid")]

    result = {
        "top": _summary(best),
        "median_engagement_rate": round(
            median([p["score"]["engagement_rate"] for p in order]), 4
        ),
        # A legfontosabb megállapítás: ugyanaz-e a legnagyobb elérésű poszt,
        # mint a legjobban teljesítő. Ha nem, akkor a költés vitte az elérést,
        # a tartalom pedig máshol működött.
        "reach_leader": _summary(by_reach) if by_reach.get("score") else None,
        "top_is_reach_leader": best.get("post_id") == by_reach.get("post_id"),
    }

    # A támogatás nélküli mezőny legjobbja: ez az, ami „magához képest” ment
    # nagyot, és amit érdemes lenne legközelebb megtámogatni.
    if unboosted:
        result["best_unboosted"] = _summary(unboosted[0])
        result["best_unboosted_beats_typical"] = (
            unboosted[0]["score"]["vs_typical"] or 0
        ) >= 1.5

    return result


def _summary(post: dict) -> dict:
    score = post.get("score") or {}
    return {
        "caption": post.get("caption", ""),
        "post_type": post.get("post_type", ""),
        "reach": int(post.get("reach") or 0),
        "vs_typical": score.get("vs_typical"),
        "engagement_rate": score.get("engagement_rate"),
        "boosted": bool(post.get("paid")),
    }
