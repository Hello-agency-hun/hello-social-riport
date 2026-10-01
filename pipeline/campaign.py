"""Deterministic data layer for a standalone, multi-month campaign report.

Unlike the monthly report, source files may cover several months. An Ads row is
never apportioned across months: Meta's unique reach and aggregated spend do
not contain the daily information needed for such a split.
"""

from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

from pipeline.detect import scan
from pipeline.errors import PipelineError
from pipeline.parsers import meta_ads, meta_content, zoomsphere, zoomsphere_performance
from pipeline.join import normalize_caption, MATCH_LENGTH
from pipeline.manual import load_manual


def _day(value, label):
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise PipelineError(f"A kampány {label} dátuma hibás: {value!r}.") from error


def _selection(values, label):
    if not isinstance(values, list):
        raise PipelineError(f"A kampány {label} mezője lista legyen.")
    result = [str(value).strip() for value in values if str(value).strip()]
    if len(result) != len(set(result)):
        raise PipelineError(f"A kampány {label} listájában ismétlődő elem van.")
    return result


def load_config(directory):
    path = Path(directory) / "campaign.yaml"
    if not path.is_file():
        raise PipelineError("Hiányzik a campaign.yaml; előbb válaszd ki a kampányhoz tartozó hirdetéseket és posztokat.")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    config = raw.get("campaign") or {}
    title = str(config.get("title") or "").strip()
    if not title:
        raise PipelineError("A kampány neve kötelező.")
    start = _day(config.get("start"), "kezdő")
    end = _day(config.get("end"), "záró")
    if end < start:
        raise PipelineError("A kampány vége nem lehet a kezdete előtt.")
    variant = config.get("variant", "full")
    if variant not in ("full", "essentials"):
        raise PipelineError("A kampány változata full vagy essentials lehet.")
    kpis = config.get("kpis") or []
    if not isinstance(kpis, list):
        raise PipelineError("A KPI-k listaként adhatók meg, és elhagyhatók.")
    for kpi in kpis:
        if not isinstance(kpi, dict) or not str(kpi.get("label") or "").strip():
            raise PipelineError("Minden megadott KPI-hoz név kell; a KPI-k opcionálisak.")
    return {
        "title": title,
        "goal": str(config.get("goal") or "").strip(),
        "start": start,
        "end": end,
        "variant": variant,
        "ads": _selection(config.get("ads") or [], "ads"),
        "posts": _selection(config.get("posts") or [], "posts"),
        "kpis": kpis,
    }


def discover(directory):
    """Return inspectable candidates, never automatically assign them to a campaign."""
    candidates = {"ads": [], "posts": [], "sources": [], "warnings": []}
    for source in scan(Path(directory) / "input"):
        if source.kind == "meta_ads":
            parsed = meta_ads.parse(source.path)
            candidates["sources"].append({"file": source.path.name, "kind": source.kind,
                                          "start": parsed.period[0].isoformat(), "end": parsed.period[1].isoformat()})
            for row in parsed.payload.campaigns:
                candidates["ads"].append({
                    "name": row.name, "file": source.path.name,
                    "start": row.report_start.isoformat(), "end": row.report_end.isoformat(),
                    "currency": row.currency, "spend": row.spend,
                })
        elif source.kind == "zoomsphere":
            parsed = zoomsphere.parse(source.path)
            candidates["sources"].append({"file": source.path.name, "kind": source.kind})
            for item in parsed.payload:
                for channel, post_id in item.post_ids.items():
                    if post_id:
                        candidates["posts"].append({
                            "key": f"{channel}:{post_id}", "published": item.published.isoformat(),
                            "channel": channel, "caption": item.caption(channel)[:160],
                            "file": source.path.name,
                        })
        elif source.kind in ("meta_content", "zoomsphere_performance"):
            parsed = (meta_content if source.kind == "meta_content" else zoomsphere_performance).parse(source.path)
            candidates["sources"].append({"file": source.path.name, "kind": source.kind})
        elif source.kind not in ("meta_daily", "pdf", "screenshot", "ignored_duplicate"):
            candidates["warnings"].append(f"Nem használt forrás: {source.path.name}")
    candidates["posts"] = list({row["key"]: row for row in candidates["posts"]}.values())
    return candidates


def build(directory):
    directory = Path(directory)
    config = load_config(directory)
    candidates = discover(directory)
    ads_selected = set(config["ads"])
    posts_selected = set(config["posts"])
    known_ads = {row["name"] for row in candidates["ads"]}
    known_posts = {row["key"] for row in candidates["posts"]}
    missing_ads = sorted(ads_selected - known_ads)
    missing_posts = sorted(posts_selected - known_posts)
    if missing_ads or missing_posts:
        raise PipelineError("A kiválasztott elem nincs az exportokban: " + ", ".join(missing_ads + missing_posts))
    if not ads_selected and not posts_selected:
        raise PipelineError("Válassz legalább egy Meta hirdetést vagy ZoomSphere-posztot a kampányhoz.")

    warnings = list(candidates["warnings"])
    ads = []
    posts = []
    content = []
    snapshots = []
    for source in scan(directory / "input"):
        if source.kind == "meta_ads":
            for row in meta_ads.parse(source.path).payload.campaigns:
                if row.name in ads_selected:
                    ads.append((row, source.path.name))
        elif source.kind == "zoomsphere":
            for item in zoomsphere.parse(source.path).payload:
                for channel, post_id in item.post_ids.items():
                    if f"{channel}:{post_id}" in posts_selected:
                        posts.append((item, channel, post_id, source.path.name))
        elif source.kind == "meta_content":
            content.extend((post, source.path.name) for post in meta_content.parse(source.path).payload)
        elif source.kind == "zoomsphere_performance":
            snapshots.extend(zoomsphere_performance.parse(source.path).payload)

    # One Ads source may legitimately contain several rows with the same name.
    # Two files covering the same days for the same campaign would double-count.
    windows = defaultdict(list)
    for row, filename in ads:
        for earlier_start, earlier_end, earlier_file in windows[row.name]:
            if filename != earlier_file and row.report_start <= earlier_end and earlier_start <= row.report_end:
                raise PipelineError(
                    f"Átfedő Meta Ads exportok a(z) {row.name} hirdetéshez: "
                    f"{earlier_file} és {filename}. Az átfedő napok kétszer számolódnának."
                )
        windows[row.name].append((row.report_start, row.report_end, filename))

    currencies = {row.currency for row, _ in ads}
    if len(currencies) > 1:
        raise PipelineError("Eltérő pénznemű Meta Ads exportokat nem lehet összeadni.")
    monthly = defaultdict(lambda: {"spend": 0.0, "impressions": 0, "link_clicks": 0, "ad_rows": 0, "posts": 0})
    unallocated = []
    detail = []
    indicative = False
    for row, filename in ads:
        within = config["start"] <= row.report_start and row.report_end <= config["end"]
        if not within:
            indicative = True
            warnings.append(f"{filename}: {row.name} lekérési ablaka túlnyúlik a kampány megadott dátumain; a szám tájékoztató jellegű.")
        one_month = row.report_start.strftime("%Y-%m") == row.report_end.strftime("%Y-%m")
        bucket = row.report_start.strftime("%Y-%m") if one_month else None
        if bucket is None:
            unallocated.append({"name": row.name, "file": filename,
                                "start": row.report_start.isoformat(), "end": row.report_end.isoformat()})
        else:
            monthly[bucket]["spend"] += row.spend
            monthly[bucket]["impressions"] += row.impressions
            monthly[bucket]["link_clicks"] += row.link_clicks
            monthly[bucket]["ad_rows"] += 1
        detail.append({
            "name": row.name, "file": filename, "report_start": row.report_start.isoformat(),
            "report_end": row.report_end.isoformat(), "started": row.start_date.isoformat() if row.start_date else None,
            "ended": row.end_date.isoformat() if row.end_date else None, "ongoing": row.is_ongoing,
            "spend": row.spend, "reach": row.reach, "impressions": row.impressions,
            "link_clicks": row.link_clicks, "results": row.results,
            "result_type": row.result_type, "monthly_bucket": bucket,
        })
    if unallocated:
        warnings.append("Több hónapot átfogó Ads-sorok nem bonthatók hitelesen havi adatokra; az összesítésben szerepelnek, külön listázva.")
    month_cursor = config["start"].replace(day=1)
    missing_months = []
    while month_cursor <= config["end"]:
        month = month_cursor.strftime("%Y-%m")
        if monthly[month]["ad_rows"] == 0 and ads_selected:
            missing_months.append(month)
        year = month_cursor.year + (month_cursor.month // 12)
        month_number = month_cursor.month % 12 + 1
        month_cursor = date(year, month_number, 1)
    if missing_months:
        warnings.append("Ezekhez a hónapokhoz nincs önálló, egy hónapra eső Meta Ads-sor: " + ", ".join(missing_months) + ". A nulla itt nem mért nullás teljesítmény.")

    measured = {}
    content_sources = {}
    for post, filename in content:
        key = (post.channel, post.post_id)
        if f"{post.channel}:{post.post_id}" not in posts_selected:
            continue
        if key in measured and measured[key] != post:
            raise PipelineError(
                f"{post.channel}:{post.post_id}: eltérő Meta Tartalom pillanatkép szerepel "
                f"a(z) {content_sources[key]} és {filename} fájlokban. "
                "Tartsd meg a használni kívánt mérési exportot; a pillanatképek nem összeadhatók."
            )
        measured[key] = post
        content_sources[key] = filename
    if snapshots:
        enriched = zoomsphere_performance.enrich(list(measured.values()), snapshots, warnings)
        measured = {(post.channel, post.post_id): post for post in enriched}
        warnings.append("ZoomSphere Performance: a posztpillanatkép nem havi mérési ablak; az elérések nem összegezhetők.")
    post_detail = []
    seen_posts = {}
    for item, channel, post_id, filename in posts:
        key = f"{channel}:{post_id}"
        if key in seen_posts:
            if seen_posts[key] == item:
                warnings.append(f"{key}: azonos ZoomSphere-poszt ismétlődött; egyszer számoltuk.")
                continue
            raise PipelineError(f"A(z) {key} poszt több ZoomSphere-exportban szerepel. Egyet tarts meg, hogy ne duplázzunk.")
        seen_posts[key] = item
        if not config["start"] <= item.published <= config["end"]:
            warnings.append(f"{key}: a poszt publikálási dátuma a kampány időszakán kívül esik.")
        bucket = item.published.strftime("%Y-%m")
        monthly[bucket]["posts"] += 1
        metric = measured.get((channel, post_id))
        post_detail.append({
            "key": key, "channel": channel, "published": item.published.isoformat(),
            "caption": item.caption(channel), "permalink": item.permalinks.get(channel, ""),
            "creatives": item.creatives.get(channel) or (metric.creatives if metric else []), "file": filename,
            "metrics_measured": metric is not None,
            "reach": metric.reach if metric else None,
            "views": metric.views if metric else None,
            "reactions": metric.reactions if metric else None,
            "comments": metric.comments if metric else None,
            "shares": metric.shares if metric else None,
            "saves": metric.saves if metric else None,
            "details": metric.details if metric else {},
        })
    # Attach only selected, uniquely matched boosts. Spend is additive across
    # disjoint export windows; unique reach is not.
    linked = defaultdict(list)
    for ad, _ in ads:
        caption = normalize_caption(ad.name)[:MATCH_LENGTH]
        matches = [post for post in post_detail if ad.is_boost and caption
                   and post['channel'] == ad.channel
                   and caption in normalize_caption(post['caption'])]
        if len(matches) == 1:
            linked[matches[0]['key']].append(ad)
        elif len(matches) > 1:
            warnings.append(f'{ad.name}: több poszthoz illeszthető; a posztköltést nem találjuk ki.')
    for post in post_detail:
        rows = linked.get(post['key'], [])
        if rows:
            post['paid'] = {'spend': round(sum(ad.spend for ad in rows), 2),
                            'currency': rows[0].currency,
                            'reach': rows[0].reach if len(rows) == 1 else None,
                            'windows': [f'{ad.report_start} – {ad.report_end}' for ad in rows]}
    if any(not post["metrics_measured"] for post in post_detail):
        warnings.append("Egyes posztokhoz nincs Meta Tartalom export; a teljesítményük ismeretlen, nem nulla.")
    if any(post["metrics_measured"] for post in post_detail):
        warnings.append("A posztok a publikálás hónapjához vannak sorolva; a Meta Tartalom export teljesítménye lekéréskori pillanatkép, nem havi interakcióösszeg.")

    return {
        "manual": load_manual(directory),
        "meta": {"type": "campaign", "title": config["title"], "goal": config["goal"],
                 "start": config["start"].isoformat(), "end": config["end"].isoformat(),
                 "variant": config["variant"], "currency": next(iter(currencies), None)},
        "summary": {"spend": round(sum(row.spend for row, _ in ads), 2),
                    "impressions": sum(row.impressions for row, _ in ads),
                    "link_clicks": sum(row.link_clicks for row, _ in ads),
                    "ad_rows": len(ads), "posts": len(post_detail),
                    "accuracy": "indicative" if indicative else "export_window",
                    "reach": None, "reach_note": "A különböző hirdetések egyedi elérése nem összeadható."},
        "monthly": {month: {**values, "ads_measured": values["ad_rows"] > 0}
                    for month, values in sorted(monthly.items())},
        "missing_ad_months": missing_months,
        "unallocated_ads": unallocated,
        "ads": detail, "posts": post_detail,
        "kpis": config["kpis"], "warnings": list(dict.fromkeys(warnings)),
        "selection": {"ads": config["ads"], "posts": config["posts"]},
    }
