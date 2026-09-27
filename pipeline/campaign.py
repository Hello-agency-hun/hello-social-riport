"""Kampányriport: egy kiválasztott kampány a saját időszakára.

Egy toborzási kampány két hónapig fut, több hirdetéssorozattal, és közben
posztokat is kiemelünk hozzá. A havi riport ezt két hónapra vágja, és elkeveri
a többi hirdetéssel — az ügyfél viszont egészen mást kérdez: **mennyibe került
egy jelentkező, eljutottunk-e a megfelelő emberekhez, és működött-e.**

A kampányriport ezért:

- csak a kiválasztott kampányokkal számol (`client.yaml` → `campaign:`),
- a kampány saját időszakára, ami nem naptári hónap,
- a hirdetési tölcsért mutatja: költés → megjelenés → elérés → kattintás →
  eredmény, mindegyik lépés arányával,
- és ha van mihez, az oldal mozgását a kampány alatt és előtte.

Ugyanazok a szabályok, mint máshol: az elérés nem adható össze (több kampány
deduplikált elérését csak az Ads Manager összesítő sora tudja), eltérő
eredménytípusok nem adhatók össze, és ami nincs, az nem nulla.
"""

import re
import unicodedata
from datetime import date, timedelta

from pipeline import periods
from pipeline.errors import MissingConfigError
from pipeline.guards import sum_results
from pipeline.kpi import money_sum
from pipeline.schema import Campaign

# Ennyi kampányt sorolunk fel a hibaüzenetben, ha a minta semmit nem talál.
LISTED = 15
# Ezeknél az eredménytípusoknál egy eredmény fillérekbe kerül: a Meta is
# ezer eredményre vetíti a költséget („1000 elérésre jutó költség”). Egy
# „0,00 EUR / eredmény” semmit nem mondana.
PER_MILLE = {"reach", "impressions"}
# Ezek az eredmények egy hivatkozáskattintásból születnek (a céloldal
# betöltése). Náluk értelmes megmondani, a kattintók hányada ért el odáig.
CLICK_BASED = {"actions:omni_landing_page_view", "actions:landing_page_view"}


def cost_per_result(spend: float, results: int, result_type: str) -> float | None:
    """Eredményenkénti költség — elérésnél és megjelenésnél ezer eredményre."""
    if not results:
        return None
    scale = 1000 if result_type in PER_MILLE else 1
    return round(spend * scale / results, 4)


# Egy kampányriport posztkártyáinak felső határa.
POST_LIMIT = 6
# A kitöltetlenül hagyott sablonmező: `"<a kampány neve a címlapon>"`.
PLACEHOLDER = re.compile(r"\s*<[^<>]*>\s*")


def _given(value):
    """A kitöltetlenül hagyott sablonmező nincs megadva — különben a helyőrző
    szövege kerülne az ügyfél címlapjára."""
    if isinstance(value, str) and PLACEHOLDER.fullmatch(value):
        return None
    return value


def yaml_lines(
    measurement_start: str | None = None,
    measurement_end: str | None = None,
    language: str | None = None,
    currency: str | None = None,
) -> list[str]:
    """A kampányriport `client.yaml`-szakaszai, kitöltendő vázként.

    A checklist és a hiányzó `client.yaml` sablonja is ezt adja — egy helyen,
    hogy a kettő ne csússzon el. A kötelező mezők helyőrzővel állnak (így
    kitöltetlenül a build megáll), az opcionálisak kommentként: ha a
    kitöltésük elmarad, nem kerül helyőrző a riportba.
    """
    lines = ["report:", "  variant: campaign"]
    if measurement_start and measurement_end:
        lines += [
            f"  measurement_start: {measurement_start}",
            f"  measurement_end: {measurement_end}",
        ]
    if language:
        lines.append(f"  language: {language}")
    if currency:
        lines.append(f"  currency: {currency}")
    return lines + [
        "campaign:",
        '  title: "<a kampány neve a címlapon>"',
        '  match: ["<a kampánynevekben közös szórészlet>"]   # kisbetű, ékezet mindegy',
        '  # goal: "<a kampány célja egy mondatban>"',
        '  # post_match: ["<#hashtag vagy kulcsszó a kapcsolódó posztokhoz>"]',
        "  # reach: <több kampánynál: az Ads Manager összesítő sorának „Elérés” értéke>",
    ]


def _fold(text: str) -> str:
    """Kis- és nagybetű, ékezet és térköz nélküli alak az illesztéshez:
    a „toborzas” megtalálja a „Toborzás_Szeged” kampányt is."""
    decomposed = unicodedata.normalize("NFKD", str(text or "").casefold())
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(plain.split())


def _ratio(numerator, denominator, digits: int):
    if not numerator and numerator != 0:
        return None
    if not denominator:
        return None
    return round(numerator / denominator, digits)


def _setup_help(campaigns: list[Campaign]) -> str:
    listed = sorted(campaigns, key=lambda c: -c.spend)[:LISTED]
    from pipeline.formatting import money

    names = "\n".join(f"  · {c.name}  ({money(c.spend, c.currency)})" for c in listed)
    more = len(campaigns) - len(listed)
    return (
        "Az exportban ezek a kampányok vannak (költés szerint):\n"
        + (names or "  (egy sincs)")
        + (f"\n  · …és még {more}" if more > 0 else "")
        + "\n\nÍrd a client.yaml-be, melyik a riport tárgya:\n\n"
        "campaign:\n"
        '  title: "<a kampány neve, ahogy a címlapon álljon>"\n'
        '  match: ["<a kampánynevekben közös szórészlet>"]   # kisbetű, ékezet mindegy\n'
        '  # names: ["<pontos kampánynév>"]                   # vagy név szerint'
    )


def select(campaigns: list[Campaign], config: dict) -> tuple[list[Campaign], list[Campaign]]:
    """(kiválasztott, többi). Semmit nem találgatunk: minta nélkül megállunk."""
    config = config or {}
    names = {_fold(name) for name in config.get("names") or [] if _given(name) and _fold(name)}
    fragments = [
        _fold(part) for part in config.get("match") or [] if _given(part) and _fold(part)
    ]
    if not _given(config.get("title")) or not (names or fragments):
        raise MissingConfigError(
            "a kampányriporthoz meg kell mondani, melyik kampányról szól.\n"
            + _setup_help(campaigns)
        )

    def wanted(campaign: Campaign) -> bool:
        name = _fold(campaign.name)
        return name in names or any(part in name for part in fragments)

    selected = [campaign for campaign in campaigns if wanted(campaign)]
    if not selected:
        raise MissingConfigError(
            "a campaign.match / campaign.names egyetlen kampányra sem illik.\n"
            + _setup_help(campaigns)
        )
    chosen = {id(campaign) for campaign in selected}
    return selected, [campaign for campaign in campaigns if id(campaign) not in chosen]


def _granularity(windows: list[tuple[date, date]]) -> str:
    lengths = sorted((end - start).days + 1 for start, end in windows)
    typical = lengths[len(lengths) // 2]
    if typical == 1:
        return "day"
    if typical <= 7:
        return "week"
    if typical >= 28:
        return "month"
    return "period"


def _merge_rows(rows: list[Campaign]) -> Campaign:
    """Egy kampány idő szerint bontott sorai — egy kampány.

    Az elérés NEM adható össze: aki két héten is látta a hirdetést, egy
    ember. Bontott exportból a kampány teljes elérése ezért ismeretlen
    (`None`), nem a hetek összege.
    """
    types = {row.result_type for row in rows if row.result_type}
    lead = max(rows, key=lambda row: row.spend)
    ongoing = any(row.is_ongoing for row in rows)
    starts = [row.start_date for row in rows if row.start_date]
    ends = [row.end_date for row in rows if row.end_date]
    return Campaign(
        name=lead.name,
        spend=money_sum(row.spend for row in rows),
        currency=lead.currency,
        reach=rows[0].reach if len(rows) == 1 else None,
        impressions=sum(row.impressions for row in rows),
        frequency=rows[0].frequency if len(rows) == 1 else None,
        link_clicks=sum(row.link_clicks for row in rows),
        results=sum(row.results for row in rows) if len(types) <= 1 else lead.results,
        # Egy hét eredmény nélkül üres típussal jön; a kampány típusa az, ami
        # a sorokban egyáltalán előfordul.
        result_type=next(iter(types)) if len(types) == 1 else lead.result_type,
        cost_per_result=0.0,
        status=lead.status,
        channel=lead.channel,
        is_boost=lead.is_boost,
        start_date=min(starts) if starts else None,
        end_date=None if ongoing or not ends else max(ends),
        is_ongoing=ongoing,
        delivery_status=lead.delivery_status,
        report_start=min((row.report_start for row in rows if row.report_start), default=None),
        report_end=max((row.report_end for row in rows if row.report_end), default=None),
    )


def consolidate(rows: list[Campaign]) -> tuple[list[Campaign], list[Campaign]]:
    """(kampányok, idősoros sorok).

    Ha a menedzser **idő szerinti bontással** exportált (Bontás → Idő → Hét),
    egy kampány több sorban jön, soronként más lekérési ablakkal. Ezeket
    kampányonként összevonjuk, a sorokat pedig megtartjuk az idővonalhoz.
    Bontás nélküli exportnál a sorok maguk a kampányok, idővonal nincs.
    """
    groups: dict[str, list[Campaign]] = {}
    for row in rows:
        groups.setdefault(row.name, []).append(row)
    broken_down = any(
        len({(row.report_start, row.report_end) for row in group}) > 1
        for group in groups.values()
    )
    if not broken_down:
        return rows, []
    return [_merge_rows(group) for group in groups.values()], rows


def timeline(rows: list[Campaign], primary: str | None) -> dict:
    """Az idő szerinti bontás pontjai: költés, megjelenés, kattintás, CTR, és
    az elsődleges eredmény — csak az, mert eltérő típusok nem adhatók össze."""
    if not rows:
        return {}
    windows: dict[tuple[date, date], list[Campaign]] = {}
    for row in rows:
        windows.setdefault((row.report_start, row.report_end), []).append(row)
    points = []
    for (start, end), group in sorted(windows.items()):
        impressions = sum(row.impressions for row in group)
        clicks = sum(row.link_clicks for row in group)
        spend = money_sum(row.spend for row in group)
        results = sum(row.results for row in group if row.result_type == primary)
        points.append(
            {
                "start": start,
                "end": end,
                "spend": spend,
                "impressions": impressions,
                "link_clicks": clicks,
                "ctr": _ratio(clicks, impressions, 4),
                "results": results if primary else None,
                "cost_per_result": cost_per_result(
                    money_sum(row.spend for row in group if row.result_type == primary),
                    results,
                    primary or "",
                ),
            }
        )
    return {"granularity": _granularity(list(windows)), "points": points}


def _row(campaign: Campaign, total_spend: float) -> dict:
    return {
        "name": campaign.name,
        "is_boost": campaign.is_boost,
        "channel": campaign.channel,
        "status": campaign.status,
        "delivery_status": campaign.delivery_status,
        "is_ongoing": campaign.is_ongoing,
        "start_date": campaign.start_date,
        "end_date": campaign.end_date,
        "spend": campaign.spend,
        "share_of_spend": _ratio(campaign.spend, total_spend, 4),
        "impressions": campaign.impressions,
        "reach": campaign.reach,
        "frequency": _ratio(campaign.impressions, campaign.reach, 2),
        "link_clicks": campaign.link_clicks,
        "ctr": _ratio(campaign.link_clicks, campaign.impressions, 4),
        "cpc": _ratio(campaign.spend, campaign.link_clicks, 2),
        "cpm": _ratio(campaign.spend * 1000, campaign.impressions, 2),
        "results": campaign.results,
        "result_type": campaign.result_type,
        "per_mille": campaign.result_type in PER_MILLE,
        "cost_per_result": cost_per_result(
            campaign.spend, campaign.results, campaign.result_type
        ),
    }


def _reach(selected: list[Campaign], config: dict) -> tuple[int | None, str | None]:
    """A kampány deduplikált elérése — ha tudható.

    Egy kampánynál az export megmondja. Többnél nem: a kampányok elérése
    átfed, az összegük több a valóságnál. Ezt csak az Ads Manager
    összesítő sora tudja (a kiválasztott kampányok alatt), onnan a menedzser
    írja be a `campaign.reach` mezőbe.
    """
    given = config.get("reach")
    if isinstance(given, int) and not isinstance(given, bool) and given > 0:
        return given, "ads_manager"
    if len(selected) == 1 and selected[0].reach:
        return selected[0].reach, "export"
    return None, None


def lift(raw_series: list, start: date, end: date) -> dict:
    """Az oldal mozgása a kampány alatt és az előtte lévő ugyanolyan hosszú
    időszakban — ha a napi csempék mindkettőt teljesen lefedik.

    Ez együttmozgás, nem bizonyított hatás: a riport így is nevezi. Részleges
    lefedésnél a mezőt kihagyjuk; hiányzó napot nullának venni hamis
    „növekedést” mutatna.
    """
    days = (end - start).days + 1
    base_start, base_end = start - timedelta(days=days), start - timedelta(days=1)
    needed = {base_start + timedelta(days=offset) for offset in range(2 * days)}
    out: dict[str, dict] = {}
    for entry in raw_series:
        sparse = entry.channel == "instagram" and entry.field == "follows"
        if sparse and (not entry.points or min(day for day, _ in entry.points) > base_start):
            # A Meta a nulla napokat ebből a csempéből kihagyja; hogy az
            # előző időszakot lefedi-e, csak az első sora mondhatja meg.
            continue
        restored = periods.filter_daily(entry, base_start, end)
        present = {day for day, _ in restored.points}
        if not needed <= present:
            continue
        during = sum(value for day, value in restored.points if day >= start)
        before = sum(value for day, value in restored.points if day < start)
        out.setdefault(entry.channel, {})[entry.field] = {
            "during": during,
            "before": before,
            "diff": during - before,
            "pct": round((during - before) / before * 100, 1) if before else None,
        }
    if not out:
        return {}
    return {
        "baseline_start": base_start,
        "baseline_end": base_end,
        "channels": out,
    }


def _related_posts(posts: list, config: dict) -> list:
    """A kampány posztjai: amelyiket a kiválasztott kampányok hirdették, és
    amelyik szövege a `post_match` valamelyik töredékét tartalmazza."""
    fragments = [
        _fold(part) for part in config.get("post_match") or [] if _given(part) and _fold(part)
    ]
    related = [
        post
        for post in posts
        if post.paid is not None
        or (fragments and any(part in _fold(post.caption) for part in fragments))
    ]
    return sorted(
        related,
        key=lambda post: (
            -(post.paid.spend if post.paid else 0),
            -(post.reactions + post.comments + post.shares),
            -post.reach,
        ),
    )[:POST_LIMIT]


def summarise(
    selected: list[Campaign],
    others: list[Campaign],
    config: dict,
    start: date,
    end: date,
    breakdown: list[Campaign],
    posts: list,
    raw_series: list,
    unmatched_boosts: list[Campaign],
) -> dict:
    """A kampányriport `campaign` blokkja — minden szám innen jön."""
    days = (end - start).days + 1
    spend = money_sum(campaign.spend for campaign in selected)
    impressions = sum(campaign.impressions for campaign in selected)
    link_clicks = sum(campaign.link_clicks for campaign in selected)
    reach, reach_source = _reach(selected, config)

    grouped: dict[str, list[Campaign]] = {}
    for campaign in selected:
        if campaign.result_type:
            grouped.setdefault(campaign.result_type, []).append(campaign)
    results = []
    for result_type, group in grouped.items():
        type_spend = money_sum(campaign.spend for campaign in group)
        count = sum_results(group)
        results.append(
            {
                "result_type": result_type,
                "campaigns": len(group),
                "spend": type_spend,
                "results": count,
                "per_mille": result_type in PER_MILLE,
                "cost_per_result": cost_per_result(type_spend, count, result_type),
            }
        )
    results.sort(key=lambda row: -row["spend"])

    wanted_type = config.get("result_type")
    primary = next(
        (row for row in results if row["result_type"] == wanted_type),
        results[0] if results else None,
    )
    if primary:
        clicks = sum(
            campaign.link_clicks
            for campaign in grouped[primary["result_type"]]
        )
        primary = {
            **primary,
            "results_per_click": (
                _ratio(primary["results"], clicks, 4)
                if primary["result_type"] in CLICK_BASED
                else None
            ),
        }

    rows = sorted((_row(campaign, spend) for campaign in selected), key=lambda row: -row["spend"])
    comparable = [
        row
        for row in rows
        if primary
        and row["result_type"] == primary["result_type"]
        and row["cost_per_result"] is not None
    ]
    best = min(comparable, key=lambda row: row["cost_per_result"]) if len(comparable) > 1 else None

    return {
        "title": str(_given(config.get("title")) or "").strip(),
        "goal": str(_given(config.get("goal")) or "").strip(),
        "start": start,
        "end": end,
        "days": days,
        "totals": {
            "campaigns": len(selected),
            "spend": spend,
            "daily_spend": _ratio(spend, days, 2),
            "impressions": impressions,
            "reach": reach,
            "reach_source": reach_source,
            "frequency": _ratio(impressions, reach, 2),
            "link_clicks": link_clicks,
            "ctr": _ratio(link_clicks, impressions, 4),
            "cpc": _ratio(spend, link_clicks, 2),
            "cpm": _ratio(spend * 1000, impressions, 2),
        },
        "results": results,
        "primary": primary,
        "best": best,
        "campaigns": rows,
        "timeline": timeline(breakdown, primary["result_type"] if primary else None),
        # Idővonalat csak valódi kezdődátumokból rajzolunk. A Meta alap
        # exportjában nincs kezdés-oszlop (csak ha a menedzser hozzáadja), és
        # a lekérési ablak eleje nem a kampány indulása — kitalált kezdéssel
        # minden kampány az időszak első napján indulna.
        "spans": (
            [
                {
                    "name": row["name"],
                    "start": row["start_date"],
                    "end": row["end_date"],
                    "ongoing": row["is_ongoing"],
                }
                for row in rows
            ]
            if rows and all(row["start_date"] for row in rows)
            else []
        ),
        "lift": lift(raw_series, start, end),
        "posts": [
            {"channel": post.channel, "post_id": post.post_id}
            for post in _related_posts(posts, config)
        ],
        "earlier_posts": [
            {"name": boost.name, "spend": boost.spend, "reach": boost.reach}
            for boost in unmatched_boosts
        ],
        "outside": {
            "campaigns": len(others),
            "spend": money_sum(campaign.spend for campaign in others),
        },
    }
