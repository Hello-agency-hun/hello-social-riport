"""A riport összeállítása. Csak a `report_data.json`-t olvassa, forrásfájlt soha."""

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import charts, formatting, i18n, images, kpi, labels
from pipeline import manual as manual_module
from pipeline import performance
from pipeline import narrative as narrative_module
from pipeline.assets import TEMPLATES, logo, review_script, stylesheet

# A formázás a `formatting` modulban él, egy helyen — a narratíva is azt
# használja, hogy egy riporton belül ne keveredjen kétféle számjelölés. Ezek a
# nevek a sablonszűrők és a meglévő tesztek kedvéért maradnak.
_number = formatting.number
_signed = formatting.signed
_money = formatting.money
_period_name = formatting.month


# Az Essentials riport rövidebb: tíz dia, és a legjobb posztok sorrendjét nem
# a rezonancia-index adja, hanem az interakciók száma. A kártyán mindkét szám
# ott van — az elérés is —, hogy látszódjon, mihez képest erős a poszt.
ESSENTIALS_POSTS = 3
TEMPLATES_BY_VARIANT = {
    "essentials": "report-essentials.html.j2",
    "full": "report.html.j2",
    "campaign": "report-campaign.html.j2",
}
# A kampánytábla egy oldalon: a sűrű sorok nyomtatásbiztos felső határa.
CAMPAIGN_ROWS_PER_PAGE = 8


def _template_name(variant) -> str:
    """Ismeretlen változatnál a teljes riport — némán rossz sablont nem adunk."""
    return TEMPLATES_BY_VARIANT.get(variant or "full", "report.html.j2")


def _interactions(post: dict) -> int:
    return sum(int(post.get(field) or 0) for field in kpi.ENGAGEMENT_FIELDS)


def _essentials_posts(posts: list[dict]) -> list[dict]:
    """A három legtöbb interakciót kapott mért poszt.

    Elérés szerint rangsorolni annyi volna, mint költés szerint. Az elérés
    így is látszik a kártyán, csak nem az dönti el a sorrendet — döntetlennél
    viszont igen.
    """
    measured = [post for post in posts if post.get("organic_measured")]
    ordered = sorted(
        measured,
        key=lambda post: (-_interactions(post), -int(post.get("reach") or 0)),
    )
    return ordered[:ESSENTIALS_POSTS]


# A 16:9-es oldal magassága kötött, a narratíva hossza nem az. A Mammut
# augusztusi riportjában a „Mi működött" panel 1119 karaktert kapott, a
# panelbe 637 pixel fért, a tartalom 678 lett — az oldal 115 pixellel
# túlcsordult. Vágni nem szabad: az ügyfélnek szánt mondat veszne el. Ezért a
# betűméret lép lejjebb, lépcsőzetesen, a hosszabbik panel szerint — a két
# panel egy rácsban ül, tehát a rövidebbik nem menti meg a másikat.
# A küszöbök a valódi oldalon mérve, böngészőben ellenőrizve: 18 px mellett
# kb. 850 karakter fér el egy panelbe (580 px széles hasáb, 1,5-es sorköz).
# Az első kalibráció engedékenyebb volt, és 1119 karakternél még maradt 19
# pixel túllógás — a küszöbök azóta a mért értékhez igazodnak.
ASSESSMENT_STEPS = ((850, 18), (1050, 16), (1400, 15))
ASSESSMENT_MIN = 14


def _assessment_font(what_worked, what_to_improve) -> int:
    """A hosszabbik panel karakterszámából a lista betűmérete."""
    longest = max(
        (sum(len(str(item)) for item in panel) for panel in (what_worked or [], what_to_improve or [])),
        default=0,
    )
    for limit, size in ASSESSMENT_STEPS:
        if longest <= limit:
            return size
    return ASSESSMENT_MIN


def _period_range(period: str) -> str:
    """`2026-07` → `2026-07-01 – 2026-07-31`.

    A korábbi, kézzel készült riportok nem naptári hónapot fedtek: a készítő
    metrikánként más napon nyitotta meg a Business Suite csempéit, így egy
    dokumentumon belül keveredtek a hónap huszonegyedikei és harmincegyedikei
    állapotok. Az átálláskor az ügyfél ezért ugrást fog látni — a riportnak ki
    kell mondania, mit mért, különben a különbség megmagyarázhatatlan.
    """
    from calendar import monthrange

    year, month = (int(part) for part in period.split("-"))
    last = monthrange(year, month)[1]
    return f"{year}-{month:02d}-01 – {year}-{month:02d}-{last}"


def _measured_range(meta: dict) -> str:
    """A ténylegesen mért időszak, a forrásfájlokból.

    Nem a naptári hónapot írjuk ki, hanem ameddig az adat ér. A menedzser nem
    mindig a hónap utolsó napján tölt le; ha ilyenkor teljes hónapot
    állítanánk, a következő havi összehasonlítás csendben torz lenne.
    """
    start = meta.get("measurement_start") or meta.get("coverage_start")
    end = meta.get("measurement_end") or meta.get("coverage_end")
    if not start or not end:
        return _period_range(meta["period"])
    return f"{start} – {end}"


def _environment(language: str = "hu") -> Environment:
    """A nyelv a szűrőkbe van kötve, nem a hívási helyekre bízva.

    Ha minden `| num` hívásnál külön át kellene adni, egy elfelejtett helyen
    magyar formátumú szám maradna az angol riportban — és ez nem hibaüzenettel
    derülne ki, hanem az ügyfélnél.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = lambda v, d=0: _number(v, d, language)
    env.filters["money"] = lambda v, c: _money(v, c, language)
    env.filters["signed"] = lambda v, d=0: _signed(v, d, language)
    env.filters["field"] = lambda k: labels.page_field(k, language)
    env.filters["result"] = lambda k: labels.result_type(k, language)
    env.filters["channel"] = labels.channel
    env.filters["ptype"] = lambda k: labels.post_type(k, language)
    env.filters["short"] = labels.shorten
    env.filters["longdate"] = lambda value: formatting.long_date(value, language)
    env.globals["date_range"] = lambda start, end: formatting.date_range(start, end, language)
    return env


def _balanced_chunks(items: list, per_page: int = 3) -> list[list]:
    """Oldalankénti bontás árva kártya nélkül.

    Négy poszt `batch(3)`-mal 3+1-re esne szét, és a második lapon egyetlen
    kártya árválkodna. Kiegyenlítve 2+2 lesz belőle.
    """
    if not items:
        return []
    pages = -(-len(items) // per_page)
    size = -(-len(items) // pages)
    return [items[i : i + size] for i in range(0, len(items), size)]


def _fixed_chunks(items: list, per_page: int = 8) -> list[list]:
    """Hard page capacity for dense rows: never exceed the print-safe limit."""
    return [items[index : index + per_page] for index in range(0, len(items), per_page)]


# Az állapotok sorrendje az összesítőben: ami fut, az elöl.
STATUS_ORDER = ("ongoing", "active", "paused", "completed", "unknown")


def _campaign_status_kind(campaign: dict) -> str:
    """Gépi állapot — a címke színe ebből jön, a felirat a nyelvből."""
    if campaign.get("is_ongoing"):
        return "ongoing"
    status = str(campaign.get("delivery_status") or campaign.get("status") or "").casefold()
    if status in {"active", "in_process", "in progress"}:
        return "active"
    if status in {"completed", "recently_completed", "finished"}:
        return "completed"
    if status in {"paused", "inactive"}:
        return "paused"
    return "unknown"


def _campaign_status(campaign: dict, text) -> str:
    return text[f"campaign_{_campaign_status_kind(campaign)}"]


def _attach_thumbnails(posts: list[dict], cache_dir: Path, fetcher, unavailable: str) -> None:
    """A kártyák képei — egy párhuzamos körben, nem posztonként egymás után.

    Ha a ZoomSphere nem tud a posztról (közvetlenül a felületen ment ki), a
    kreatív hiányzik, de a Facebook és az Instagram `og:image`-e megvan.
    Kiegészítés, nem forrás: ha nem jön össze, marad a helyőrző, és a
    `--validate` akkor is felsorolja a posztot.
    """
    orphans = [post for post in posts if not post["creatives"] and post.get("permalink")]
    recovered = images.parallel(
        lambda post: images.creative_from_permalink(post["permalink"], fetcher=fetcher),
        orphans,
    )
    fallback: dict[int, str] = {}
    for post, (found, why) in zip(orphans, recovered):
        # Az indoklást akkor is eltesszük, ha sikerült: a menedzser csak így
        # tudja eldönteni, érdemes-e kézzel pótolni a képet.
        post["creative_recovery"] = why
        if found:
            fallback[id(post)] = found

    sources = [(post["creatives"][:1] or [fallback.get(id(post))])[0] for post in posts]
    uris = images.embed(
        [source for source in sources if source], cache_dir=cache_dir, fetcher=fetcher
    )
    embedded = iter(uris)
    for post, source in zip(posts, sources):
        thumb = next(embedded) if source else images.PLACEHOLDER
        # A helyőrző is a riport nyelvén szól: az angol riportban egy „kép
        # nem elérhető” felirat hanyagságnak látszana.
        post["thumb"] = images.placeholder(unavailable) if thumb == images.PLACEHOLDER else thumb


def _campaign_view(data: dict, language: str, text, cache_dir: Path, fetcher) -> dict:
    """A kampányriport oldalaihoz kellő, már formázott részletek.

    Minden szám a `campaign` blokkból jön; itt csak diagram, lapozás és
    kép készül belőle.
    """
    block = data["campaign"]
    currency = data["paid"]["currency"]
    money = lambda value: formatting.money(value, currency, language)  # noqa: E731
    count = lambda value: formatting.number(value, 0, language)  # noqa: E731
    percent = lambda value: formatting.percent(value, 1, language)  # noqa: E731

    points = (block.get("timeline") or {}).get("points") or []
    timeline_charts = []
    if points:
        series = {
            "spend": (text.campaign_spend, money),
            "impressions": (text.campaign_impressions, count),
            "results": (text.campaign_results_over_time, count),
            "ctr": (text.campaign_ctr, percent),
        }
        colours = ["var(--accent)", "var(--brand-blue)", "var(--brand-rose)", "var(--brand-pink)"]
        for index, (key, (title, fmt)) in enumerate(series.items()):
            values = [
                (date.fromisoformat(point["start"]), point[key])
                for point in points
                if point.get(key) is not None
            ]
            if not values:
                continue
            timeline_charts.append(
                (
                    title,
                    charts.line_chart(
                        values,
                        label=f"{block['title']} — {title}",
                        height=175,
                        colour=colours[index % len(colours)],
                        language=language,
                        total_label=text.total,
                        empty_label=text.no_data,
                        # Aránynál és összegnél a tört tető és a saját formátum kell;
                        # az arányok összege értelmetlen, ezért ott nincs összesen.
                        value_format=None if fmt is count else fmt,
                        show_total=key != "ctr",
                    ),
                )
            )

    gantt = None
    if block.get("spans"):
        gantt = charts.gantt(
            [
                {
                    **span,
                    "start": date.fromisoformat(span["start"]) if span["start"] else None,
                    "end": date.fromisoformat(span["end"]) if span["end"] else None,
                }
                for span in block["spans"]
            ],
            date.fromisoformat(block["start"]),
            date.fromisoformat(block["end"]),
            label=f"{block['title']} — {text.campaign_when}",
            language=language,
            empty_label=text.no_data,
        )

    rows = []
    for row in block["campaigns"]:
        shown = dict(row)
        shown["status_kind"] = _campaign_status_kind(row)
        shown["display_status"] = _campaign_status(row, text)
        shown["is_best"] = bool(block.get("best")) and row["name"] == block["best"]["name"]
        rows.append(shown)

    wanted = {(item["channel"], item["post_id"]) for item in block.get("posts") or []}
    posts = [
        post
        for channel in data.get("channels", {}).values()
        for post in channel["posts"]
        if (post["channel"], post["post_id"]) in wanted
    ]
    _attach_thumbnails(posts, cache_dir, fetcher, text.image_unavailable)

    lift = block.get("lift") or {}
    lift_rows = [
        {"channel": channel, "field": field, **values}
        for channel, fields in (lift.get("channels") or {}).items()
        for field, values in fields.items()
    ]

    return {
        "timeline_charts": _balanced_chunks(timeline_charts, per_page=4),
        "gantt": gantt,
        "row_pages": _fixed_chunks(rows, per_page=CAMPAIGN_ROWS_PER_PAGE),
        "post_pages": _balanced_chunks(posts),
        "lift_rows": lift_rows,
    }


def _report_identity(data: dict) -> dict:
    """Ez az egy riport — a böngészőoldali mentés ehhez kötődik.

    A `review.js` a félkész munkát (kézi számok, megjegyzések, átírt
    szövegek) a böngésző tárhelyében őrzi. Ez a tárhely eredetenként közös:
    ha minden riport ugyanarról a szerverről nyílik meg, egy közös kulcs
    mellett az egyik ügyfél kézi adatai és megjegyzései a másik ügyfél
    `review.json`-jába kerültek. A kulcs ezért az ügyfél, a pontos időszak és
    a változat; a `revision` pedig az adott renderelés, hogy egy már
    feldolgozott kör megjegyzései ne kerüljenek vissza a következőbe.
    """
    meta = data.get("meta") or {}
    key = "|".join(
        str(meta.get(field) or "")
        for field in ("client", "period", "measurement_start", "measurement_end", "variant")
    )
    return {"key": key, "revision": date.today().isoformat() + ":" + _fingerprint(data)}


def _fingerprint(data: dict) -> str:
    import hashlib

    raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def render(
    data: dict,
    cache_dir: Path,
    narrative: dict | None = None,
    fetcher: Callable[[str], bytes] = images.fetch,
    manual: dict | None = None,
) -> str:
    # A nyelv a riportadatból jön, az pedig a `client.yaml`-ből. Egy helyen
    # dől el, és onnantól a szűrők, a feliratok és a diagramok is ezt követik.
    language = data["meta"].get("language") or i18n.DEFAULT
    text = i18n.strings(language)

    if narrative:
        narrative_module.check_language(narrative, language)
    resolved = (
        narrative_module.resolve_all(narrative, data, markup=True)
        if narrative
        else None
    )

    campaign_rows = []
    for campaign in data.get("paid", {}).get("campaign_details", []):
        row = dict(campaign)
        row["status_kind"] = _campaign_status_kind(campaign)
        row["display_status"] = _campaign_status(campaign, text)
        row["display_end"] = (
            text.campaign_ongoing
            if campaign.get("is_ongoing")
            else campaign.get("end_date") or text.campaign_unknown
        )
        campaign_rows.append(row)
    # Az első oldalon a narratíva és az állapotösszesítő is helyet kér. Nyolc
    # sor hosszabb kampányneveknél a lábléc alá csúszik; a folytatásoldalakon
    # viszont, ahol nincs bevezető blokk, továbbra is elfér nyolc sor.
    campaign_pages = []
    if campaign_rows:
        campaign_pages = [campaign_rows[:6]]
        campaign_pages.extend(_fixed_chunks(campaign_rows[6:], per_page=8))
    # (gépi állapot, felirat, darab) — a futó kampányok elöl. Korábban ábécé
    # szerint álltak, így a „lezárult” megelőzhette az „aktív”-at.
    counted = Counter(row["status_kind"] for row in campaign_rows)
    campaign_status_counts = [
        (kind, text[f"campaign_{kind}"], counted[kind])
        for kind in STATUS_ORDER
        if counted[kind]
    ]
    # Az eredménytípusok költés szerint csökkenő sorrendben: ami a keret
    # nagyobbik részét vitte, az van felül.
    result_rows = sorted(
        (data.get("paid", {}).get("by_result_type") or {}).items(),
        key=lambda item: -(item[1].get("spend") or 0),
    )

    credibility = data.get("meta", {}).get("measurement_credibility")
    period_warning = {
        "gap": text.period_gap_warning,
        "overlap": text.period_overlap_warning,
        "nonstandard": text.period_nonstandard_warning,
        "assumed": text.period_assumed_warning,
    }.get(credibility)
    if data.get("campaign") and credibility != "assumed":
        # Egy kampány időszaka szándékosan nem naptári hónap, és nem az előző
        # hónaphoz mérjük: a havi hitelességi figyelmeztetés itt félrevezetne.
        period_warning = None

    organic = data["cross"]["organic_reach"]
    boosted = data["cross"]["boosted_reach"]

    # Egy oldalon négy görbe fut; ha mind zöld, összemosódnak. A ciklus a
    # márkapaletta hangosabb színeit is behozza, nem csak az akcentust.
    curve_colours = [
        "var(--accent)",
        "var(--brand-rose)",
        "var(--brand-blue)",
        "var(--brand-pink)",
    ]

    trends = {}
    for name, block in data.get("channels", {}).items():
        trend_charts = [
            (
                labels.page_field(field, language),
                charts.line_chart(
                    [
                        (date.fromisoformat(day), value)
                        for day, value in block["daily"][field]
                    ],
                    label=f"{labels.channel(name)} — {labels.page_field(field, language)}",
                    height=175,
                    colour=curve_colours[index % len(curve_colours)],
                    language=language,
                    total_label=text.total,
                    empty_label=text.no_data,
                ),
            )
            for index, field in enumerate(sorted(block["daily"]))
        ]
        # Legfeljebb négy trenddiagram fér el biztonságosan egy 16:9-es
        # oldalon. Öt mérőszámnál az ötödik korábban a lábléc alá csúszott.
        trends[name] = _balanced_chunks(trend_charts, per_page=4)

    channel_posts = {}
    ranking: dict[str, str] = {}
    # A kampányriport a saját posztjait mutatja (`_campaign_view`); a havi
    # rangsor képeit ott fölösleges volna letölteni.
    monthly_channels = {} if data.get("campaign") else data.get("channels", {})
    for name, block in monthly_channels.items():
        # Teljesítmény szerint, nem elérés szerint. Elérés szerint rangsorolni
        # annyi volna, mint költés szerint: amelyik posztra a legtöbb pénz ment,
        # az lenne elöl — ez tautológia, nem megállapítás. Lásd `performance.py`.
        essentials = data.get("meta", {}).get("variant") == "essentials"
        ranked = performance.balanced(block["posts"], limit=6)
        if not ranked:
            # Nincs mért elérés ezen a csatornán — marad a régi sorrend, hogy
            # a boostolt posztok legalább megjelenjenek.
            ranked = sorted(block["posts"], key=lambda post: -post["reach"])
        selected = (
            _essentials_posts(block["posts"])
            if essentials
            else [post for post in ranked if post["reach"]][:6]
        )
        if not selected:
            # Ezen a csatornán nincs mért elérés — a boostoltakat emeljük ki,
            # mert azokról van mért fizetett adatunk.
            selected = [post for post in ranked if post.get("paid")][:6]
        _attach_thumbnails(selected, cache_dir, fetcher, text.image_unavailable)
        channel_posts[name] = _balanced_chunks(selected)
        # Az elérés szerinti rangsor egy pillantással megmutatja a sorrendet,
        # amit a kártyák oldalanként háromra bontva nem tudnak.
        # A diagram azt mutatja, hányszorosa a poszt a csatorna szokásos
        # teljesítményének — nem az elérést, mert azt a költés dönti el.
        # A `score` önmagában még nem jelent összehasonlítható szorzót. Ha egy
        # mezőny mediánja nulla, a `vs_typical` szándékosan None; ezt nullaként
        # kirajzolni azt hazudná, hogy a poszt 0,0-szeresen teljesített.
        measured = [
            post
            for post in selected
            if post.get("score") and post["score"].get("vs_typical") is not None
        ]
        if measured:
            ranking[name] = charts.bar_chart(
                [
                    (
                        labels.shorten(post["caption"], 44) or text.no_caption,
                        post["score"]["vs_typical"] or 0,
                    )
                    for post in measured
                ],
                label=f"{labels.channel(name)} — {text.performance_vs_typical}",
                language=language,
                value_format=lambda value: formatting.multiplier(value, language),
                empty_label=text.no_data,
            )

    template = _environment(language).get_template(
        _template_name(data.get("meta", {}).get("variant"))
    )
    campaign_view = (
        _campaign_view(data, language, text, cache_dir, fetcher)
        if data.get("campaign")
        else None
    )
    return template.render(
        campaign=data.get("campaign"),
        campaign_view=campaign_view,
        page_title=(data.get("campaign") or {}).get("title"),
        data=data,
        trends=trends,
        channel_posts=channel_posts,
        ranking=ranking,
        # A módszertani oldal egyszer szerepel, az első olyan csatorna előtt,
        # ahol egyáltalán van pontozott poszt. Vakon az első csatornához kötve
        # kimaradna, ha épp azon nincs mért elérés.
        methodology_channel=next(
            (
                name
                for name, chunks in channel_posts.items()
                if chunks and chunks[0] and chunks[0][0].get("score")
            ),
            None,
        ),
        narrative=resolved,
        # A narratíva hossza az OpenAI-tól jön, az oldal magassága kötött —
        # a lista betűmérete ezért a szövegből számolódik, nem fix.
        assessment_font=_assessment_font(
            (resolved or {}).get("what_worked") or [],
            (resolved or {}).get("what_to_improve") or [],
        ),
        campaign_narrative=(resolved or {}).get("campaign_status") or {},
        # Az Essentials csatornánként egy rövid összefoglalót mutat. Ha a
        # narratíva nem tartalmazza, a dia a számokkal áll meg — kitalálni
        # nem találunk ki hozzá szöveget.
        essentials_overview={
            name: (resolved or {}).get(f"{name}_overview")
            for name in data.get("channels", {})
            if (resolved or {}).get(f"{name}_overview")
        },
        campaign_pages=campaign_pages,
        campaign_status_counts=campaign_status_counts,
        result_rows=result_rows,
        ads_period=data.get("quality", {}).get("ads_period") or {},
        css=stylesheet(),
        logo_lockup=logo("hello-lockup"),
        logo_mark=logo("hello-mark"),
        t=text,
        # A gombfeliratok a JavaScriptbe is átmennek: az a kód a sablonon kívül
        # él, és az angol próbán pont ezek maradtak magyarul.
        ui_labels=json.dumps(i18n.ui(language), ensure_ascii=False),
        report_identity=_report_identity(data),
        period_name=_period_name(data["meta"]["period"], language),
        period_range=_measured_range(data["meta"]),
        period_warning=period_warning,
        coverage_partial=data["meta"].get("coverage_partial", False),
        generated=date.today().isoformat(),
        charts={
            "reach_split": charts.donut(
                [(text.boosted_posts_label, boosted), (text.organic_posts_label, organic)],
                label=text.reach_split_label,
                language=language,
                empty_label=text.no_data,
            ),
        },
        currency=data["paid"]["currency"],
        manual=manual or {},
        manual_slots=manual_module.SLOTS,
        review_js=review_script(),
    )
