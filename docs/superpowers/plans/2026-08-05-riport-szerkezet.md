# HELLO Reporting — 3. terv: Riport-szerkezet

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A 10 oldalas adatkiíratásból csatornánként tagolt, 16-18 oldalas ügyfélriport — teljes kreatívokkal, napi trendgörbékkel, csatornánként hat kiemelt poszttal, és az előző időszakhoz mért változással.

**Architecture:** A `report_data.json` szerkezete bővül (`channels` blokk csatornánként), a renderelés szekciókra bomlik. A meglévő elv nem változik: minden szám kódból jön. Ami változik: **ami nem mérhető, az nem kerül az ügyfél elé módszertani mentegetőzésként** — a hiánylista a `--validate` kimenetében és a JSON-ban marad.

**Tech Stack:** ugyanaz — Jinja2, Pillow, inline SVG. Új függőség nincs.

**Előfeltétel:** az 1. és 2. terv kész (145 teszt zöld).

---

## Miért készül ez a terv

A 2. terv riportja működik, de három dologban nem elég jó:

1. **A kreatívok fele levágódik.** `object-fit: cover` 264 px-en — az álló poszt-képek középső sávja látszik.
2. **Nincs csatorna-bontás.** A Mammut riport külön Instagram- és Facebook-szekcióval dolgozik, hat kiemelt poszttal csatornánként. Nálam egy közös tábla van, három poszttal.
3. **A 31 napos idősorok kihasználatlanok.** Csatornánként 4 metrika × 31 nap adat van a rendszerben, és csak az összegük jelenik meg.

Plusz egy tartalmi hiba, amit én okoztam: a négy Instagram-boostot „nem illesztett"-ként írtam ki az ügyfélnek. **A költésük végig benne volt az összesítésben** — csak poszt szinten nem mutattam őket, mert a poszt-táblát a Meta Tartalom exportból építem, és Instagram Tartalom export nincs. A ZoomSphere viszont tartalmazza az Instagram-posztokat, és a hirdetés kampányneve illeszkedik rájuk: **mérve 4/4**. Vagyis megjelenítési hiányt címkéztem adathiánynak.

---

## Az új oldalszerkezet

| # | Oldal | Feltétel |
|---|---|---|
| 1 | Címlap | — |
| 2 | A hónap számokban | — |
| 3 | Mit csináltunk (tartalomnaptár) | — |
| 4 | **Instagram** — KPI-csempék | van IG adat |
| 5 | Instagram — napi trendek | van IG idősor |
| 6 | Instagram — változás az előző hónaphoz | van előző időszak |
| 7-8 | Instagram — kiemelt posztok (3+3) | van IG poszt |
| 9 | **Facebook** — KPI-csempék | van FB adat |
| 10 | Facebook — napi trendek | van FB idősor |
| 11 | Facebook — változás az előző hónaphoz | van előző időszak |
| 12-13 | Facebook — top posztok (3+3) | van FB poszt |
| 14 | Fizetett — always-on kampányok | van kampány |
| 15 | Fizetett — boostolt posztok | van boost |
| 16 | Organikus és fizetett | — |
| 17 | Összefoglaló | — |
| 18 | Záró, kontakt | — |

**Maximum 18 oldal.**

### Hiányzó adat: kitölthető mező, nem néma kihagyás

Ha egy szekcióhoz nincs adat, **két különböző okból lehet**, és a kettőt máshogy kell kezelni:

| Ok | Kezelés |
|---|---|
| Az adat **nem létezik** (nincs IG poszt-metrika, nincs story-teljesítmény) | a szekció kimarad |
| Az adat **létezik, csak nincs letöltve** (havi elérés, követőszám, előző hónap) | a szekció **megjelenik kitölthető mezővel** |

A második eset a fontos. Ha csendben kihagynánk, a menedzser sosem tudná meg,
hogy egyáltalán létezik ilyen adat. Helyette a riportban ott a hely, szaggatott
kerettel, és a mező alatt az, hogy **honnan szerezhető be**.

A menedzser beleírja a böngészőben, megnyomja a Mentést, és a `manual.json`
lekerül a hónap mappájába. A következő futásnál már kitöltve jelenik meg,
diszkrét „kézi adat" jelöléssel.

**Az üres mezők nyomtatásban nem jelennek meg** — az ügyfélhez soha nem megy ki
üres keret. A képernyőn viszont ott vannak, hogy ne merüljön feledésbe, mi hiányzik.

### Csatornánként mit tudunk

|  | Instagram | Facebook |
|---|---|---|
| Oldal-szintű napi metrika | ✅ 4 db (felkeresés, kattintás, interakció, megtekintés) | ✅ 4 db (felkeresés, követés, interakció, kattintás) |
| Poszt-szintű organic | ❌ nincs IG Tartalom export | ✅ 16 poszt |
| Poszt kreatív + szöveg + link | ✅ ZoomSphere | ✅ ZoomSphere |
| Poszt-szintű fizetett | ✅ 4 boost | ✅ 4 boost |

Ezért az Instagram poszt-oldala **a boostolt posztokat** emeli ki (kreatív, költés, fizetett elérés), a Facebooké **a hat legnagyobb elérésűt**. Amint megjön az IG Tartalom export, az IG oldal automatikusan átvált elérés szerinti rangsorra — a sablon ugyanaz marad.

### Poszt-metrikák megjelenítése

Két **mért** szám, kivonás nélkül:

```
Elérés               9 046
ebből fizetett       8 398        15,95 EUR
Reakció                 22
Hozzászólás              1
Megosztás                1
Kattintás            1 186
```

Organikus elérést nem számolunk ki kivonással: az összes elérés és a kampány-elérés halmaza átfed, a különbség nem tiszta organikus érték.

---

## Task 1: Csatorna-blokk az adatmodellben

**Files:** Modify `pipeline/kpi.py`, `pipeline/build.py`; Test: `tests/test_kpi.py`

- [ ] **Step 1: Írd meg a failing tesztet** — fűzd a `tests/test_kpi.py` végéhez:

```python
def test_channel_block_groups_everything_by_channel(input_file):
    from pipeline.kpi import channel_blocks
    from pipeline.parsers import meta_daily

    series = [
        meta_daily.parse(input_file(name)).payload
        for name in (
            "Felkeresések.csv",
            "Hivatkozáskattintások.csv",
            "Interakciók.csv",
            "Követők.csv",
        )
    ]
    blocks = channel_blocks(series=series, posts=[], campaigns=[])
    facebook = blocks["facebook"]
    assert facebook["totals"]["visits"] == 1525
    assert facebook["totals"]["follows"] == 5
    assert len(facebook["daily"]["visits"]) == 31
    assert facebook["daily"]["visits"][0] == ["2026-07-01", 33]


def test_channel_block_is_empty_for_a_channel_without_data(input_file):
    from pipeline.kpi import channel_blocks
    from pipeline.parsers import meta_daily

    series = [meta_daily.parse(input_file("Felkeresések.csv")).payload]
    blocks = channel_blocks(series=series, posts=[], campaigns=[])
    assert "instagram" not in blocks
```

- [ ] **Step 2: Futtasd, hogy elbukjon** — `pytest tests/test_kpi.py -q` → `ImportError: cannot import name 'channel_blocks'`

- [ ] **Step 3: Bővítsd a `pipeline/kpi.py`-t**

```python
def channel_blocks(series: list, posts: list, campaigns: list) -> dict:
    """Csatornánként egy blokk: napi idősorok, összegek, posztok, boostok.

    A riport csatornánként külön szekciót kap, ezért az adat is így áll össze.
    Ami egy csatornáról nincs, az nem szerepel benne — nem nulla, nem üres kulcs.
    """
    blocks: dict[str, dict] = {}

    for entry in series:
        block = blocks.setdefault(
            entry.channel, {"daily": {}, "totals": {}, "posts": [], "boosts": []}
        )
        block["daily"][entry.field] = [
            [day.isoformat(), value] for day, value in entry.points
        ]
        block["totals"][entry.field] = sum_additive(
            [value for _, value in entry.points], field=entry.field
        )

    for post in posts:
        block = blocks.setdefault(
            post.channel, {"daily": {}, "totals": {}, "posts": [], "boosts": []}
        )
        block["posts"].append(post)

    for campaign in campaigns:
        if campaign.is_boost and campaign.channel:
            block = blocks.setdefault(
                campaign.channel, {"daily": {}, "totals": {}, "posts": [], "boosts": []}
            )
            block["boosts"].append(campaign)

    return blocks
```

- [ ] **Step 4: Kösd be a `build.py`-ba**

A visszaadott szótárba, a `"page"` kulcs mellé:

```python
            "channels": kpi.channel_blocks(
                series=series, posts=joined.posts, campaigns=campaigns
            ),
```

- [ ] **Step 5: Futtasd** — `pytest tests/test_kpi.py tests/test_build.py -q` → a build-tesztek elbuknak a golden eltérés miatt; ez várt. Generáld újra:

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 \
  --out tests/fixtures/larus-2026-07/report_data.golden.json \
  --html /tmp/x.html --offline
```

Majd `pytest -q` → minden zöld.

- [ ] **Step 6: Commit**

```bash
git add pipeline/kpi.py pipeline/build.py tests/test_kpi.py tests/fixtures/larus-2026-07/report_data.golden.json
git commit -m "feat: csatornankenti adatblokk a riport-szekciokhoz"
```

---

## Task 2: Instagram-posztok a ZoomSphere-ből

Ez zárja le a „nem illesztett boost" ügyet. Az Instagram-posztok a ZoomSphere-ből
épülnek fel — kreatívval, szöveggel, linkkel —, és a hirdetés a szöveg alapján
kapcsolódik hozzájuk. Organikus metrika nem lesz mellettük; ha később megjön az
IG Tartalom export, az felülírja őket.

**Files:** Modify `pipeline/join.py`; Test: `tests/test_join.py`

- [ ] **Step 1: Írd meg a failing tesztet** — fűzd a `tests/test_join.py` végéhez:

```python
def test_instagram_posts_are_built_from_zoomsphere(input_file):
    """IG Tartalom export nélkül is meg tudjuk mutatni a boostolt IG-posztokat.

    A költésük eddig is benne volt az összesítésben; ami hiányzott, az a
    poszt-szintű megjelenítés kreatívval.
    """
    result = join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    )
    instagram = [post for post in result.posts if post.channel == "instagram"]
    boosted = [post for post in instagram if post.is_boosted]
    assert len(boosted) == 4
    assert result.unmatched_boosts == []
    for post in boosted:
        assert post.creatives, "kreatív nélkül nincs értelme megmutatni"
        assert post.caption
        assert post.reach == 0, "IG organikus elérés nincs mérve — nem találjuk ki"


def test_facebook_posts_still_come_from_the_content_export(input_file):
    result = join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    )
    facebook = [post for post in result.posts if post.channel == "facebook"]
    assert len(facebook) == 16
    assert max(post.reach for post in facebook) == 9046
```

- [ ] **Step 2: Futtasd, hogy elbukjon** — `pytest tests/test_join.py -q`

- [ ] **Step 3: Bővítsd a `pipeline/join.py`-t**

A `join_posts` 2. lépése (Ads boostok) **elé** illeszd be:

```python
    # 1b. Amelyik csatornáról nincs Tartalom export, ott a ZoomSphere-ből
    # építünk poszt-objektumot. Organikus metrika nélkül — azt nem találjuk ki.
    measured = {post.channel for post in result.posts}
    for item in items:
        if item.post_type == "story":
            continue
        for channel, post_id in item.post_ids.items():
            if not post_id or channel in measured:
                continue
            result.posts.append(
                Post(
                    channel=channel,
                    post_id=post_id,
                    published=item.published,
                    caption=item.caption(channel),
                    permalink=item.permalinks.get(channel, ""),
                    post_type=item.post_type,
                    creatives=item.creatives.get(channel, []),
                )
            )
```

- [ ] **Step 4: Futtasd** — `pytest tests/test_join.py -q` → `9 passed`

- [ ] **Step 5: Generáld újra a goldent és futtasd a teljes készletet**

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 \
  --out tests/fixtures/larus-2026-07/report_data.golden.json --html /tmp/x.html --offline
pytest -q
```

A `--validate` kimenetében a „nem illesztett boost" sornak most **nincs**-re kell váltania.

- [ ] **Step 6: Commit**

```bash
git add pipeline/join.py tests/test_join.py tests/fixtures/larus-2026-07/report_data.golden.json
git commit -m "feat: IG-posztok a ZoomSphere-bol, a boostok mar poszt szinten is lathatok"
```

---

## Task 3: Teljes kreatív, vágás nélkül

**Files:** Modify `templates/brand.css`; Test: `tests/test_brand.py`

- [ ] **Step 1: Írd meg a failing tesztet** — fűzd a `tests/test_brand.py` végéhez:

```python
def test_creatives_are_shown_whole_not_cropped():
    """Álló poszt-képnél a `cover` levágná a kreatív felét."""
    text = CSS.read_text(encoding="utf-8")
    thumb = text[text.index(".thumb") : text.index(".thumb") + 400]
    assert "object-fit: contain" in thumb
    assert "cover" not in thumb
```

- [ ] **Step 2: Futtasd, hogy elbukjon** — `pytest tests/test_brand.py -q`

- [ ] **Step 3: Írd át a `.thumb` szabályt a `templates/brand.css`-ben**

```css
/* A kreatívok álló (4:5, 9:16) és fekvő arányban is érkeznek. `cover` esetén az
   álló képek közepét vágnánk ki — a poszt fele eltűnne. `contain` mellett a
   teljes kreatív látszik, a keret pedig semleges háttérrel tölti ki a helyet. */
.thumb { display: block; width: 100%; height: 300px;
         object-fit: contain; border-radius: 8px; background: var(--rule); }
```

- [ ] **Step 4: Futtasd** — `pytest tests/test_brand.py -q` → `14 passed`

- [ ] **Step 5: Commit**

```bash
git add templates/brand.css tests/test_brand.py
git commit -m "fix: a kreativok teljes egeszukben latszanak, nem vagva"
```

---

## Task 4: Napi trend-oldalak

**Files:** Modify `pipeline/render.py`; Create `templates/sections/trends.html.j2`; Test: `tests/test_render.py`

- [ ] **Step 1: Írd meg a failing tesztet** — fűzd a `tests/test_render.py` végéhez:

```python
def test_each_channel_gets_daily_trend_charts(html):
    assert html.count('class="chart"') >= 8, "csatornánként 4 metrika trendgörbéje"


def test_trend_chart_labels_are_hungarian(html):
    assert "Felkeresések" in html
    assert "Interakciók" in html
```

- [ ] **Step 2: Futtasd, hogy elbukjon** — `pytest tests/test_render.py -q`

- [ ] **Step 3: A `render()`-ben építsd fel a csatornánkénti trendeket**

A `charts={...}` szótár mellé, előtte:

```python
    from datetime import date as _date

    trends = {}
    for name, block in data.get("channels", {}).items():
        trends[name] = [
            (
                labels.page_field(field),
                charts.line_chart(
                    [
                        (_date.fromisoformat(day), value)
                        for day, value in block["daily"][field]
                    ],
                    label=f"{labels.channel(name)} — {labels.page_field(field)}",
                ),
            )
            for field in sorted(block["daily"])
        ]
```

és add át a sablonnak: `trends=trends,`

- [ ] **Step 4: Írd meg a `templates/sections/trends.html.j2`-t**

```jinja
{% for name, block in data.channels.items() %}
{% if block.daily %}
<section class="page">
  <div class="eyebrow">{{ name | channel }}</div>
  <h2 style="margin-bottom:30px">Napi alakulás</h2>
  <div class="grid" style="grid-template-columns:1fr 1fr">
    {% for title, svg in trends[name] %}
    <div class="panel">
      <h3 style="font-size:15px;margin-bottom:10px">{{ title }}</h3>
      {{ svg | safe }}
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}
{% endfor %}
```

Illeszd be a `report.html.j2`-be az oldal-teljesítmény szekció helyére:

```jinja
{% include "sections/trends.html.j2" %}
```

- [ ] **Step 5: Futtasd** — `pytest tests/test_render.py -q`

- [ ] **Step 6: Commit**

```bash
git add pipeline/render.py templates/ tests/test_render.py
git commit -m "feat: csatornankenti napi trendgorbek"
```

---

## Task 5: Csatorna-szekciók KPI-csempékkel és poszt-oldalakkal

**Files:** Create `templates/sections/channel.html.j2`; Modify `templates/report.html.j2`, `pipeline/render.py`; Test: `tests/test_render.py`

- [ ] **Step 1: Írd meg a failing tesztet**

```python
def test_report_has_a_section_per_channel(html):
    assert html.count(">Instagram<") >= 1
    assert html.count(">Facebook<") >= 1


def test_six_posts_are_shown_per_channel_when_available(html):
    """Facebookon 16 mért poszt van — hatot mutatunk, két oldalon."""
    assert html.count('class="thumb"') >= 6


def test_post_metrics_show_measured_numbers_not_a_subtraction(html):
    """Összes elérés és fizetett kampány-elérés — organikus becslés nélkül."""
    assert "ebből fizetett" in html
    assert "becsült" not in html.lower()


def test_page_count_stays_within_the_agreed_limit(html):
    assert 12 <= html.count('class="page') <= 20
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: Írd meg a `templates/sections/channel.html.j2`-t**

```jinja
{% for name, block in data.channels.items() %}
{% set shown = channel_posts[name] %}

{% if block.totals %}
<section class="page">
  <div class="eyebrow">{{ name | channel }}</div>
  <h2 style="margin-bottom:44px">A hónap teljesítménye</h2>
  <div class="grid" style="grid-template-columns:repeat(3,1fr)">
    {% for field, value in block.totals.items() %}
    <div class="panel">
      <div class="stat">{{ value | num }}</div>
      <div class="stat-label">{{ field | field }}</div>
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

{% for chunk in shown | batch(3) %}
<section class="page">
  <div class="eyebrow">{{ name | channel }} · kiemelt posztok</div>
  <h2 style="margin-bottom:26px">{{ "A legnagyobb elérésű tartalmak" if block.posts and block.posts[0].reach else "A hónap kiemelt tartalmai" }}</h2>
  <div class="grid" style="grid-template-columns:repeat(3,1fr)">
    {% for post in chunk %}
    <div class="panel">
      <img class="thumb" src="{{ post.thumb }}" alt="">
      <p style="margin-top:12px;color:var(--ink);font-size:15px">{{ post.caption[:80] }}</p>
      <div class="rule" style="margin:12px 0"></div>
      <table style="font-size:14px">
        {% if post.reach %}
        <tr><td>Elérés</td><td class="num"><strong>{{ post.reach | num }}</strong></td></tr>
        {% endif %}
        {% if post.paid %}
        <tr><td class="accent">ebből fizetett</td>
            <td class="num accent"><strong>{{ post.paid.reach | num }}</strong></td></tr>
        <tr><td class="accent">költés</td>
            <td class="num accent">{{ post.paid.spend | money(currency) }}</td></tr>
        {% endif %}
        {% if post.reactions %}
        <tr><td>Reakció</td><td class="num">{{ post.reactions | num }}</td></tr>
        {% endif %}
        {% if post.clicks %}
        <tr><td>Kattintás</td><td class="num">{{ post.clicks | num }}</td></tr>
        {% endif %}
      </table>
    </div>
    {% endfor %}
  </div>
</section>
{% endfor %}
{% endfor %}
```

- [ ] **Step 4: A `render()`-ben állítsd elő a `channel_posts` szótárt**

```python
    channel_posts = {}
    for name, block in data.get("channels", {}).items():
        ranked = sorted(block["posts"], key=lambda post: -post["reach"])
        selected = [post for post in ranked if post["reach"]][:6]
        if not selected:
            # Nincs mért elérés ezen a csatornán — a boostoltakat emeljük ki,
            # mert azokról van mért fizetett adatunk.
            selected = [post for post in ranked if post.get("paid")][:6]
        for post in selected:
            uris = images.embed(
                post["creatives"][:1], cache_dir=cache_dir, fetcher=fetcher
            )
            post["thumb"] = uris[0] if uris else images.PLACEHOLDER
        channel_posts[name] = selected
```

Add át: `channel_posts=channel_posts,`

Cseréld a `report.html.j2` régi „Top posztok" szekcióit erre:

```jinja
{% include "sections/channel.html.j2" %}
```

- [ ] **Step 5: Futtasd** — `pytest -q`

- [ ] **Step 6: Commit**

```bash
git add pipeline/render.py templates/ tests/test_render.py
git commit -m "feat: csatorna-szekciok KPI-csempekkel es hat poszttal"
```

---

## Task 6: A módszertan-oldal átalakítása

Az ügyfél elé nem hiánylista kerül, hanem az, hogy mit csináltunk. A hiányok a
`--validate` kimenetében és a `report_data.json`-ban maradnak — a menedzsernek
ugyanúgy látszanak, csak nem a kiküldött dokumentumban.

**Files:** Modify `templates/report.html.j2`; Test: `tests/test_render.py`

- [ ] **Step 1: Írd meg a failing tesztet**

```python
def test_report_does_not_apologise_to_the_client(html):
    """A hiánylista a menedzsernek szól, nem az ügyfélnek.

    A `--validate` és a report_data.json változatlanul tartalmazza — az ügyfél
    elé kerülő dokumentum azt mutatja, mit csináltunk, nem azt, mit nem tudunk.
    """
    for phrase in ("nem illesztett", "Nem becsültük meg", "nem közöl ilyen számot"):
        assert phrase not in html


def test_quality_block_still_records_everything(data):
    """A belső szigor nem lazul: a JSON-ban minden hiány rögzítve marad."""
    assert "unmatched_boosts" in data["quality"]
    assert "unmatched_content" in data["quality"]
    assert "dropped_zero_campaign_rows" in data["quality"]
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: Írd át a módszertani oldalt a `report.html.j2`-ben**

Cseréld a teljes „Módszertan" szekciót erre:

```jinja
<section class="page">
  <div class="eyebrow">Összefoglaló</div>
  <h2 style="margin-bottom:40px">A hónap mérlege</h2>
  <div class="grid" style="grid-template-columns:repeat(3,1fr)">
    <div>
      <div class="stat">{{ data.content.total }}</div>
      <div class="stat-label">kiküldött tartalom</div>
    </div>
    <div>
      <div class="stat">{{ data.cross.post_reach_sum | num }}</div>
      <div class="stat-label">poszt-elérés</div>
    </div>
    <div>
      <div class="stat">{{ data.paid.spend | money(currency) }}</div>
      <div class="stat-label">hirdetési költés</div>
    </div>
    <div>
      <div class="stat accent">{{ data.cross.avg_reach_boosted_post | num }}</div>
      <div class="stat-label">boostolt poszt átlagos elérése</div>
    </div>
    <div>
      <div class="stat">{{ data.cross.avg_reach_organic_post | num }}</div>
      <div class="stat-label">organikus poszt átlagos elérése</div>
    </div>
    <div>
      <div class="stat accent">{{ data.cross.reach_multiplier | num(1) }}×</div>
      <div class="stat-label">a boost szorzója</div>
    </div>
  </div>
  <p class="note" style="margin-top:auto">
    Az adatok forrása a Meta Business Suite és a ZoomSphere hivatalos exportja.
    Készült: {{ generated }}.
  </p>
</section>
```

- [ ] **Step 4: Futtasd** — `pytest -q`

- [ ] **Step 5: Ellenőrizd, hogy a `--validate` továbbra is jelent**

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 --validate
```

A kimenetben ott kell lennie a „nem illesztett boost" sornak (most: `nincs`).

- [ ] **Step 6: Commit**

```bash
git add templates/report.html.j2 tests/test_render.py
git commit -m "feat: az ugyfel-riport azt mutatja, mit csinaltunk, nem a hianyokat"
```

---

## Task 7: Előző időszak — összehasonlítás

**Files:** Create `pipeline/compare.py`; Modify `pipeline/build.py`, `pipeline/render.py`; Test: `tests/test_compare.py`

- [ ] **Step 1: Írd meg a failing tesztet** — `tests/test_compare.py`:

```python
import json

import pytest

from pipeline.compare import deltas, load_previous


def test_delta_is_absolute_and_relative():
    result = deltas({"visits": 1525, "follows": 5}, {"visits": 1000, "follows": 5})
    assert result["visits"] == {"now": 1525, "before": 1000, "diff": 525, "pct": 52.5}
    assert result["follows"]["pct"] == 0.0


def test_missing_previous_metric_is_omitted_not_zero():
    """Ha egy metrika nem volt az előző hónapban, nem írunk 0%-ot."""
    result = deltas({"visits": 100, "views": 50}, {"visits": 80})
    assert "views" not in result


def test_zero_before_yields_no_percentage():
    result = deltas({"visits": 100}, {"visits": 0})
    assert result["visits"]["diff"] == 100
    assert result["visits"]["pct"] is None


def test_load_previous_returns_none_when_absent(tmp_path):
    assert load_previous(tmp_path) is None


def test_load_previous_reads_the_json(tmp_path):
    (tmp_path / "previous.json").write_text(
        json.dumps({"channels": {"facebook": {"totals": {"visits": 9}}}}),
        encoding="utf-8",
    )
    assert load_previous(tmp_path)["channels"]["facebook"]["totals"]["visits"] == 9
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: Írd meg a `pipeline/compare.py`-t**

```python
"""Összehasonlítás az előző időszakkal.

Forrása a hónap mappájában lévő `previous.json` — legegyszerűbben az előző havi
`report_data.json` átmásolva. Ha nincs, az összehasonlító oldalak kimaradnak;
kitalált változást nem közlünk.
"""

import json
from pathlib import Path


def load_previous(directory: Path) -> dict | None:
    path = Path(directory) / "previous.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def deltas(now: dict, before: dict) -> dict:
    """Csak azokra a metrikákra, amelyek mindkét időszakban szerepelnek."""
    result = {}
    for key, value in now.items():
        if key not in before:
            continue
        previous = before[key]
        diff = value - previous
        result[key] = {
            "now": value,
            "before": previous,
            "diff": diff,
            "pct": round(diff / previous * 100, 1) if previous else None,
        }
    return result
```

- [ ] **Step 4: Kösd be a `build.py`-ba**

```python
    previous = compare.load_previous(directory)
    ...
            "comparison": (
                {
                    name: compare.deltas(
                        block["totals"],
                        previous.get("channels", {}).get(name, {}).get("totals", {}),
                    )
                    for name, block in channels.items()
                }
                if previous
                else {}
            ),
```

- [ ] **Step 5: Írd meg a `templates/sections/comparison.html.j2`-t**

Az oldal **akkor is megjelenik, ha nincs előző időszak** — ilyenkor a Task 8b-ben
készülő kézi mezőkkel, hogy a menedzser be tudja írni a múlt havi számokat.

```jinja
{% for name, block in data.comparison.items() %}
{% if block %}
<section class="page">
  <div class="eyebrow">{{ name | channel }}</div>
  <h2 style="margin-bottom:44px">Változás az előző hónaphoz</h2>
  <div class="grid" style="grid-template-columns:repeat(3,1fr)">
    {% for field, d in block.items() %}
    <div class="panel">
      <div class="stat {{ 'accent' if d.diff > 0 else '' }}">
        {{ '↑' if d.diff > 0 else ('↓' if d.diff < 0 else '·') }} {{ d.now | num }}
      </div>
      <div class="stat-label">{{ field | field }}</div>
      <p class="note" style="margin-top:8px">
        előző hónap: {{ d.before | num }}{% if d.pct is not none %} · {{ d.pct | num(1) }}%{% endif %}
      </p>
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}
{% endfor %}
```

Illeszd be a `report.html.j2`-be a trend-szekció után.

- [ ] **Step 6: Futtasd** — `pytest -q`

- [ ] **Step 7: Commit**

```bash
git add pipeline/compare.py pipeline/build.py pipeline/render.py templates/ tests/test_compare.py
git commit -m "feat: osszehasonlitas az elozo idoszakkal, ha van adat"
```

---

## Task 8: Előző riport importálása PDF-ből

Az első hónapban nincs `previous.json` — a menedzser viszont rendelkezik az előző
riporttal PDF-ben. Ebből ki lehet olvasni a számokat, **de nem szabad némán
elhinni őket**: a PDF idegen elrendezésű lehet, és a `149.3K` alakú számok
kerekítettek. Ezért a script **javaslatot** ad, amit a menedzser megerősít.

**Files:** Create `tools/import_previous.py`; Test: `tests/test_import_previous.py`

- [ ] **Step 1: Írd meg a failing tesztet** — `tests/test_import_previous.py`:

```python
import pytest

from tools.import_previous import parse_compact_number, harvest


@pytest.mark.parametrize(
    "text, expected",
    [
        ("149.3K", 149300),
        ("81.6K", 81600),
        ("4.9K", 4900),
        ("852", 852),
        ("+200", 200),
        ("1 227", 1227),
    ],
)
def test_compact_numbers_are_expanded(text, expected):
    assert parse_compact_number(text) == expected


def test_unparseable_text_returns_none():
    assert parse_compact_number("kb. sok") is None


def test_harvest_returns_labelled_candidates():
    lines = ["Instagram", "1 4 9 . 3 K", "Impressions", "8 1 . 6 K", "Reach"]
    found = harvest(lines)
    assert found["impressions"] == 149300
    assert found["reach"] == 81600
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: Írd meg a `tools/import_previous.py`-t**

```python
"""Előző havi riport számainak kinyerése PDF-ből — javaslatként.

Az első hónapban nincs `previous.json`, csak a korábbi riport PDF-je. Ebből ki
lehet olvasni a kulcsszámokat, de **nem megbízhatóan**: idegen elrendezés,
betűközzel szedett számjegyek, és `149.3K` alakú kerekítés. Ezért a script nem
ír `previous.json`-t, hanem **javaslatot nyomtat**, amit a menedzser ellenőriz.

A második hónaptól erre nincs szükség: az előző havi `report_data.json` pontos.

Használat:
    python tools/import_previous.py "<elozo riport.pdf>"
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.textio import force_utf8_output  # noqa: E402

LABELS = {
    "impressions": ("impression", "megjelenés", "megtekint"),
    "reach": ("reach", "elérés"),
    "interactions": ("interaction", "interakció"),
    "visits": ("visit", "felkeres"),
    "link_clicks": ("link click", "hivatkozáskattint"),
    "followers": ("follower", "követ"),
}


def parse_compact_number(text: str) -> int | None:
    cleaned = re.sub(r"[\s ]", "", str(text)).lstrip("+")
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)([KkMm]?)", cleaned)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    scale = {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2).lower()]
    return int(round(value * scale))


def harvest(lines: list[str]) -> dict[str, int]:
    """Szám–felirat párok: a riportokban a felirat a szám alatt áll."""
    found: dict[str, int] = {}
    numbers: list[int] = []
    for line in lines:
        collapsed = re.sub(r"(?<=\S) (?=\S)", "", line.strip())
        value = parse_compact_number(collapsed)
        if value is not None:
            numbers.append(value)
            continue
        lowered = line.lower()
        for key, needles in LABELS.items():
            if key not in found and any(n in lowered for n in needles) and numbers:
                found[key] = numbers[-1]
    return found


def main(pdf_path: Path) -> int:
    import pymupdf

    document = pymupdf.open(pdf_path)
    lines: list[str] = []
    for page in document:
        lines += (page.get_text() or "").splitlines()

    found = harvest(lines)
    if not found:
        print("Nem találtam felismerhető számot a PDF-ben.")
        return 1

    print(f"{pdf_path.name} — javaslat, ELLENŐRIZD:\n")
    for key, value in found.items():
        print(f"  {key:14} {value:>10,}".replace(",", " "))
    print(
        "\nEzek kerekített értékek lehetnek (pl. 149.3K → 149 300).\n"
        "Ha stimmelnek, írd be őket a hónap mappájában lévő previous.json-be:\n"
        '  {"channels": {"facebook": {"totals": {...}}, "instagram": {"totals": {...}}}}'
    )
    return 0


if __name__ == "__main__":
    force_utf8_output()
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
```

- [ ] **Step 4: Futtasd a teszteket** — `pytest tests/test_import_previous.py -q` → `8 passed`

- [ ] **Step 5: Próbáld ki a valódi Mammut riporton**

```bash
python tools/import_previous.py Mammut_july_social_riport_2026.pdf
```

Vesd össze a kiírt számokat a PDF-fel. **A Mammut riport betűközzel szedett
számokat tartalmaz** (`1 4 9 . 3 K`) — ha a script ezeket nem ismeri fel,
az a `harvest` összevonó regexének hibája; javítsd, ne a tesztet.

- [ ] **Step 6: Commit**

```bash
git add tools/import_previous.py tests/test_import_previous.py
git commit -m "feat: elozo riport szamainak kinyerese PDF-bol, javaslatkent"
```

---

## Task 8b: Kézi adatmezők

Ez a task valósítja meg a fenti elvet: ami hiányzik, de beszerezhető, az látható
és kitölthető marad.

**Files:** Create `pipeline/manual.py`, `templates/macros.html.j2`, `templates/manual.js`; Modify `pipeline/render.py`, `pipeline/build.py`, `pipeline/cli.py`, `templates/brand.css`, `templates/print.css`; Test: `tests/test_manual.py`

- [ ] **Step 1: Írd meg a failing tesztet** — `tests/test_manual.py`:

```python
import json
from pathlib import Path

import pytest

from pipeline.manual import SLOTS, load_manual

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)


def test_missing_file_yields_an_empty_mapping(tmp_path):
    assert load_manual(tmp_path) == {}


def test_values_are_read_from_manual_json(tmp_path):
    (tmp_path / "manual.json").write_text(
        json.dumps({"reach_facebook": 92400}), encoding="utf-8"
    )
    assert load_manual(tmp_path)["reach_facebook"] == 92400


def test_every_slot_says_where_to_get_it():
    """A mező önmagában semmit nem ér — meg kell mondania, honnan szerezhető be."""
    for key, slot in SLOTS.items():
        assert slot["label"], key
        assert slot["hint"], f"{key}: nincs megadva, honnan szerezhető be"


@pytest.fixture
def data():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture
def empty(data, tmp_path):
    from pipeline.render import render

    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def test_empty_slot_is_visible_on_screen(empty):
    assert 'data-manual="reach_facebook"' in empty
    assert "Business Suite" in empty


def test_empty_slot_is_hidden_when_printing(empty):
    css = empty[empty.index("<style>") : empty.index("</style>")]
    printed = css[css.index("@media print") :]
    assert ".manual-slot" in printed and "display: none" in printed


def test_filled_slot_renders_as_a_value(data, tmp_path):
    from pipeline.render import render

    html = render(
        data,
        cache_dir=tmp_path,
        fetcher=lambda url: b"",
        manual={"reach_facebook": 92400},
    )
    assert "92 400" in html.replace("\u00a0", " ")
    assert "kézi adat" in html
    assert 'data-manual="reach_facebook"' not in html
```

- [ ] **Step 2: Futtasd, hogy elbukjon** — `pytest tests/test_manual.py -q`

- [ ] **Step 3: Írd meg a `pipeline/manual.py`-t**

```python
"""Kézzel bevitt értékek.

Vannak számok, amiket a Meta nem exportál, de a felületén ott vannak (havi
deduplikált elérés, követő-összlétszám). Ezeket a menedzser olvassa le és írja be.

Az elv: **ami hiányzik, de beszerezhető, az látható marad.** Ha csendben
kihagynánk, a menedzser sosem tudná meg, hogy létezik ilyen adat. Ezért a
riportban megjelenik a hely, azzal együtt, hogy honnan szerezhető be.
"""

import json
from pathlib import Path

SLOTS = {
    "reach_facebook": {
        "label": "Facebook havi elérés",
        "hint": "Business Suite → Elérés csempe, havi időszakra állítva",
    },
    "reach_instagram": {
        "label": "Instagram havi elérés",
        "hint": "Business Suite → Elérés csempe, havi időszakra állítva",
    },
    "followers_facebook": {
        "label": "Facebook követők",
        "hint": "Business Suite → Közönség; a következő hónapban már automatikus",
    },
    "followers_instagram": {
        "label": "Instagram követők",
        "hint": "Business Suite → Közönség; a következő hónapban már automatikus",
    },
}


def load_manual(directory: Path) -> dict:
    path = Path(directory) / "manual.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Írd meg a `templates/macros.html.j2`-t**

```jinja
{% macro slot(key, value, label, hint) %}
{% if value is not none %}
<div>
  <div class="stat">{{ value | num }}</div>
  <div class="stat-label">{{ label }} <span class="manual-mark">kézi adat</span></div>
</div>
{% else %}
<div class="manual-slot no-print" data-manual="{{ key }}">
  <div class="manual-input" contenteditable="true" data-placeholder="—"></div>
  <div class="stat-label">{{ label }}</div>
  <p class="note" style="margin-top:6px">{{ hint }}</p>
</div>
{% endif %}
{% endmacro %}
```

- [ ] **Step 5: Egészítsd ki a `templates/brand.css`-t**

```css
/* Kézi adat: ami hiányzik, de beszerezhető, az látható és kitölthető marad.
   Nyomtatásban viszont soha nem megy ki üres keret az ügyfélhez. */
.manual-slot { border: 1.5px dashed var(--rule); border-radius: 12px; padding: 20px; }
.manual-input { font-size: 48px; font-weight: 900; line-height: 1;
                min-height: 50px; outline: none; color: var(--ink); }
.manual-input:empty::before { content: attr(data-placeholder); color: var(--rule); }
.manual-input:focus { border-bottom: 2px solid var(--accent); }
.manual-mark { font-weight: 500; color: var(--accent); letter-spacing: 0; }
```

és a `templates/print.css` `@media print` blokkjába:

```css
  .manual-slot { display: none !important; }
```

- [ ] **Step 6: Írd meg a `templates/manual.js`-t**

```javascript
// A kézi mezők mentése. A böngésző lokális fájlba nem tud írni, letöltést
// viszont tud indítani — a manual.json onnan kerül a hónap mappájába.
(function () {
  var KEY = "hello-report-manual";
  var fields = document.querySelectorAll("[data-manual]");
  if (!fields.length) return;

  var stored = JSON.parse(localStorage.getItem(KEY) || "{}");

  function read() {
    var out = {};
    fields.forEach(function (field) {
      var raw = field.querySelector(".manual-input").textContent;
      var value = parseInt(raw.replace(/[^0-9]/g, ""), 10);
      if (!isNaN(value)) out[field.dataset.manual] = value;
    });
    return out;
  }

  fields.forEach(function (field) {
    var input = field.querySelector(".manual-input");
    if (stored[field.dataset.manual]) {
      input.textContent = stored[field.dataset.manual];
    }
    input.addEventListener("input", function () {
      localStorage.setItem(KEY, JSON.stringify(read()));
    });
  });

  var button = document.createElement("button");
  button.className = "pdf-button no-print";
  button.style.right = "190px";
  button.textContent = "Kézi adatok mentése";
  button.onclick = function () {
    var blob = new Blob([JSON.stringify(read(), null, 2)], {
      type: "application/json",
    });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "manual.json";
    link.click();
  };
  document.body.appendChild(button);
})();
```

- [ ] **Step 7: Kösd be a `render()`-be**

Vedd fel a `manual: dict | None = None` paramétert, és add át a sablonnak:

```python
        manual=manual or {},
        manual_slots=manual_module.SLOTS,
        manual_js=(TEMPLATES / "manual.js").read_text(encoding="utf-8"),
```

A `report.html.j2` elejére `{% from "macros.html.j2" import slot %}`, a `</body>`
elé pedig `<script>{{ manual_js | safe }}</script>`.

Az összefoglaló oldalra tedd ki a négy mezőt:

```jinja
  <div class="grid" style="grid-template-columns:repeat(4,1fr);margin-top:36px">
    {% for key, meta in manual_slots.items() %}
    {{ slot(key, manual.get(key), meta.label, meta.hint) }}
    {% endfor %}
  </div>
```

A `build.py` olvassa be a `manual.json`-t (`manual.load_manual(directory)`), tegye
be a `report_data.json`-be `manual` kulcs alatt, a `cli.py` pedig adja át a
`render()`-nek.

- [ ] **Step 8: Futtasd** — `pytest -q`

- [ ] **Step 9: Commit**

```bash
git add pipeline/manual.py templates/ tests/test_manual.py pipeline/render.py pipeline/build.py pipeline/cli.py
git commit -m "feat: kezi adatmezok - ami hianyzik de beszerezheto, az lathato marad"
```

---

## Task 9: Vizuális ellenőrzés

**Files:** —

- [ ] **Step 1: Generáld le a riportot valódi képekkel**

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 \
  --out /tmp/report_data.json --html /tmp/Riport.html
```

- [ ] **Step 2: Nyisd meg böngészőben, és nézd végig oldalanként**

- [ ] 16-18 oldal, egyik sem üres és egyik sem csordul túl
- [ ] a kreatívok **teljes egészükben** látszanak, nincs levágva a felük
- [ ] Instagram-szekció: KPI-csempék, 4 trendgörbe, 4 boostolt poszt kreatívval
- [ ] Facebook-szekció: KPI-csempék, 4 trendgörbe, 6 poszt két oldalon
- [ ] a poszt-metrikáknál „Elérés" és „ebből fizetett" is látszik
- [ ] nincs a riportban „nem illesztett", „nem becsültük", „nem közöl"
- [ ] `Ctrl+P` → oldalanként egy szekció, nem elcsúszva
- [ ] minden szám magyar formátumú (szóköz ezres, vessző tizedes)
- [ ] a kézi mezők szaggatott kerettel látszanak, és **kiírják, honnan szerezhetők be**
- [ ] beleírsz egy kézi mezőbe → „Kézi adatok mentése" → `manual.json` letöltődik
- [ ] a `manual.json`-t a mappába téve és újrafuttatva a szám kitöltve jelenik meg
- [ ] `Ctrl+P` előnézetben az **üres** kézi mezők nem látszanak

- [ ] **Step 3: Ha bármi nem stimmel, javítsd — és írj rá tesztet**

A 2. tervnél öt hiba csak a kész riportra ránézve derült ki. Ez a lépés nem
formalitás.

- [ ] **Step 4: Commit**

---

## Ami a 4. tervre marad

`SKILL.md` és a plugin-telepítés · export-varázsló a hiányzó fájlokra ·
`narrative.json` séma és a szám-ellenőrzés · a narratíva-oldalak (vezetői
összefoglaló, kulcsmegállapítás, „mi működött", akcióterv) · `review.js`
szerkesztéssel és megjegyzésekkel · `--apply-review`.

**A narratíva a legfontosabb, ami még hiányzik.** Ez a terv a vázat adja meg;
attól lesz riport, hogy valaki elmondja, mit jelentenek a számok.
