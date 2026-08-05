# HELLO Reporting — omnichannel havi riport skill

**Dátum:** 2026-08-05
**Státusz:** Design jóváhagyva, implementációra vár
**Készítette:** Mészáros Péter + Claude (brainstorming session)

---

## 1. Cél

Egy telepíthető Claude Code plugin, amellyel a HELLO Agency social media menedzserei
**egyetlen paranccsal** összeállítanak egy ügyfélnek kiküldhető havi teljesítményriportot
a ZoomSphere, a Meta organic és a Meta paid adataiból.

A kimenet egy önálló, brandelt HTML fájl, amely böngészőből PDF-be nyomtatható.

### Amit kivált

A mai folyamat: a menedzser letölt 8-12 exportot, screenshotol a Meta felületén,
mindezt bedobja a ChatGPT-be, és onnan kér grafikonokat meg elemzéseket.
Ez lassú, ügyfelenként máshogy néz ki, és **a számokat egy LLM állítja elő** —
összeadásokat, arányokat, összehasonlításokat, ellenőrzés nélkül.

### Sikerkritérium

1. A menedzser ~6 perc export-letöltés után egy paranccsal megkapja a kész riportot.
2. A riportban szereplő minden szám kódból származik, és visszavezethető egy forrásfájlra.
3. Minden ügyfél riportja ugyanúgy néz ki és ugyanúgy olvasható.
4. Ami nem mérhető, az nem szerepel a riportban kitalált számként.

---

## 2. Hatókör

### Benne van (v1)

- ZoomSphere Scheduler XLSX export feldolgozása (content calendar, kreatívok, poszt ID-k)
- Meta Ads Manager kampány-szintű CSV export
- Meta Business Suite **Tartalom** export (poszt-szintű organic teljesítmény)
- Meta Business Suite **Eredmények** napi CSV-k (oldal-szintű metrikák)
- Kézi kiegészítő adatok (havi reach, követő-összlétszám) varázslón keresztül
- Interaktív export-varázsló hiányzó fájlokhoz
- HTML riport + PDF nyomtatás
- Ügyfelenkénti konfiguráció: nyelv, pénznem, KPI-választás, szekció ki/be

### Nincs benne (v1)

- **Google Ads** — a szekció-architektúra előkészíti, de v1-ben nem implementált (v2)
- **MCP / API integráció** — minden adat kézi exportból jön (v2+)
- **Story-teljesítmény** — sehol nem elérhető adat; a story mennyiségként és kreatívként szerepel
- Automatikus e-mail kiküldés
- Több hónapos trendriport (a havi összehasonlítás benne van, hosszabb idősor nem)

### Kifejezetten nem csináljuk

- **Havi deduplikált reach kiszámítása** részadatokból. Matematikailag alulhatározott
  (halmazméretek ismertek, metszetek nem). Kézi bevitel vagy semmi.
- **Poszt-szintű metrika becslése** napi aggregátumokból dátum-hozzárendeléssel.
- Bármilyen szám előállítása LLM-mel.

---

## 3. Adatforrások

Minden forrás manuális export. A parser **tartalom alapján** azonosítja a fájlokat,
nem fájlnév alapján — a menedzsernek nem kell átneveznie semmit.

### 3.1 ZoomSphere Scheduler export (XLSX)

23 oszlop, egy sor = egy publikált tartalom.

| Oszlop | Tartalom |
|---|---|
| `Datetime` | `01.07.2026 - 11:00 AM` formátum |
| `PostType` | `image` / `story` / `reel` |
| `Status` | `Published` |
| `FacebookMessage`, `InstagramMessage` | copy szöveg |
| `FacebookPostIDs` | `154826691204747_1490635643107254` (oldal_poszt) |
| `InstagramPostIDs` | `17957904336154653` |
| `FacebookPublicPermalinks`, `InstagramPublicPermalinks` | publikus linkek |
| `FacebookImages`, `InstagramImages` | S3 kreatív URL-ek, vesszővel elválasztva |
| `InstagramFileUrl` / `Thumbnail`, `FacebookFileUrl` / `Thumbnail` | story kreatívok (Backblaze) |
| `FacebookVideoUrl`, `InstagramVideoUrl` | videó kreatívok |

**Metrikát nem tartalmaz.** Szerepe: content calendar + kreatív + join kulcs.

Referencia-adat (Larus, 2026 július): 29 sor — 14 image, 14 story (7 FB + 7 IG), 1 reel.

### 3.2 Meta Ads Manager kampány export (CSV)

27 oszlop, magyar fejlécekkel, UTF-8. Egy sor = egy kampány.

Kulcsoszlopok: `Kampány neve`, `Kampány teljesítése`, `Eredmények`,
`Eredmény jelzése`, `Elérés`, `Gyakoriság`, `Elköltött összeg (EUR)`,
`Megjelenések`, `CPM`, `Hivatkozáskattintások`, `CPC`, `CTR`,
`Érkezésioldal-megtekintések`.

Kezelendő sajátosságok:

- **Pénznem az oszlopfejlécben van** (`Elköltött összeg (EUR)`), ügyfelenként eltér.
  Detektálni kell, nem beégetni.
- **Az `Eredmények` oszlop polimorf.** Az `Eredmény jelzése` mondja meg, mit jelent:
  `reach`, `actions:omni_landing_page_view`, `profile_visit_view`,
  `actions:post_engagement`, `actions:link_click`,
  `actions:click_to_call_native_call_placed`. **Különböző típusok nem adhatók össze.**
- **Sok a zaj.** Larus júliusban: 31 sorból 18 csupa nulla (inaktív kampány az
  időablakban). Szűrendő, de a szűrt darabszám logolandó.
- **Két kampány-archetípus van egy fájlban:**
  - *always-on kampányok* — `larus_event_b2b_nyár`, `Lóvasút_B2B_*` (100-300 EUR keret, lead cél)
  - *boostolt posztok* — `Bejegyzés: „…"` / `Instagram-bejegyzés: …` (2-16 EUR, láthatóság)

  A prefix egyben a csatornát is megadja.

### 3.3 Meta Business Suite — Tartalom export (CSV)

33 oszlop, UTF-8. Egy sor = egy feed poszt. **Csatornánként külön export** (FB / IG fiókváltóval).

Kulcsoszlopok: `Bejegyzésazonosító`, `Oldalazonosító`, `Oldal neve`, `Cím` (copy),
`Közzététel időpontja`, `Állandó hivatkozás`, `Bejegyzés típusa`,
`Megtekintések`, `Elérés`, `Reakciók`, `Hozzászólások`, `Megosztások`,
`Összes kattintás`, `Egyéb kattintások`, `Hivatkozáskattintások`,
`Megtekintett Másodperc`, `Átlagosan megtekintett Másodperc`.

Megjegyzések:

- A `Bejegyzésazonosító` a ZoomSphere ID **második fele** (oldal-prefix nélkül) → utótag-illesztés.
- A `Fizetett tartalom állapota` oszlop üresen jön — **a paid jelölés az Ads joinból származik**, nem innen.
- Az `Elérés` **teljes elérés, a fizetettet is tartalmazza**. A riport ezt így is címkézi.
- **Story-t nem tartalmaz**, csak feed posztokat (`Fényképek` / `Hivatkozások` / `Videók`).

### 3.4 Meta Business Suite — Eredmények napi CSV-k

**UTF-16 LE kódolás**, első sor `sep=,`, **második sorban a metrika neve**, harmadik sor
`"Dátum","Primary"`, majd napi sorok.

A fájlnév használhatatlan (`Felkeresések.csv` / `Felkeresések-2.csv`), a metrika-azonosítás
a 2. sorból történik. A referencia-adatban megfigyelt metrikanevek:

| Metrikanév a fájlban | Csatorna |
|---|---|
| `Facebook-felkeresések` | FB |
| `Facebook-követések` | FB |
| `Tartalomnál végzett műveletek` | FB |
| `Facebookos hivatkozáskattintások` | FB |
| `Instagram-profilfelkeresések` | IG |
| `Instagramos hivatkozáskattintások` | IG |
| `Interakció tartalmaknál` | IG |
| `Megtekintések` | IG |

A referencia-készletből hiányzik a FB megtekintés-csempe és az IG követés-csempe —
ezek léteznek a felületen, csak nem lettek letöltve, így a pontos metrikanevük
még nem ismert. A parser **ismeretlen metrikanév esetén nem áll le**, hanem
felsorolja a fel nem ismert fájlokat, és megkérdezi, melyik metrikához tartoznak;
a választ a `client.yaml`-be menti, így legközelebb már felismeri.

**Fontos:** ezek a page-szintű számok a fizetett aktivitást is tartalmazzák.
Bizonyíték a referencia-adatban: a FB hivatkozáskattintások júl. 27-30. között
303/184/238/305 (a havi 1 227 kattintás 68%-a 4 nap alatt), miközben a
`larus_event_b2b_nyár` és `Lóvasút_B2B_esküvő` kampányok futottak.
A riport ezért **„oldal összes"** címkével jeleníti meg, nem „organic"-ként.

### 3.5 Kézi kiegészítés (`page_metrics.yaml`)

Amit egyik export sem tartalmaz, és számítással sem állítható elő:

| Adat | Honnan | Gyakoriság |
|---|---|---|
| Havi deduplikált reach (FB, IG) | Business Suite → Elérés csempe, havi időszak | havonta |
| Követő-összlétszám (FB, IG) | Business Suite | csak az első hónapban, utána az előző riport zárószáma |

### 3.6 Export-checklist (a varázsló gerince)

A `references/export-guide.md` tartalma. Ügyfelenként ~6 perc.
A részletesség lépésenként eltérő: az Ads Manager-részt a menedzserek ismerik,
ott elég egy emlékeztető; a Tartalom fül és az Eredmények csempék részletes vezetést kapnak.

| # | Honnan | Mit | Fájl |
|---|---|---|---|
| 1 | ZoomSphere → Scheduler → Export | teljes hónap | `export_*.xlsx` |
| 2 | Ads Manager → Kampányok → Exportálás | mentett oszlopsablon, hónapra szűrve | `*-Kampányok-*.csv` |
| 3 | Business Suite → Statisztika → Tartalom → Export | **FB oldal** | `<dátum>_*.csv` |
| 4 | ugyanott, fiókváltóval | **IG fiók** | `<dátum>_*.csv` |
| 5 | Statisztika → Eredmények, csempénként | FB: felkeresések, követések, interakciók, hivatkozáskattintások, megtekintések | 5 CSV |
| 6 | ugyanez IG-re | IG: profilfelkeresések, követések, interakciók, hivatkozáskattintások, megtekintések | 5 CSV |
| 7 | Elérés csempe, **havi** időszakra állítva | 2 szám (FB + IG) | varázsló kérdezi |
| 8 | Követő-összlétszám | 2 szám, csak az első hónapban | varázsló kérdezi |

**Átnevezés nincs.** A menedzser bedobja a fájlokat az `input/` mappába úgy, ahogy
letöltötte; a `detect.py` tartalom alapján azonosítja őket.

A varázsló csak a **hiányzó** elemekről kérdez. Ha minden fájl megvan, az `export-guide.md`
be sem töltődik a kontextusba.

---

## 4. Architektúra

### 4.1 Alapelv: a lezárt adatvonal

```
exportok
   │
   ▼
① parsers/          forrásonként külön parser
   │
   ▼
② schema.py         egységes adatmodell
   │
   ▼
③ join.py           post ID + caption illesztés
   │
   ▼
④ kpi.py            összegek, arányok, összehasonlítás
   │
   ▼
   report_data.json     ═══ LEZÁRT VONAL ═══
   │
   ├──▶ ⑤ Claude  →  narrative.json     (csak olvas, számot nem állít elő)
   │
   ▼
⑥ render.py + template  →  Riport.html
```

**A lezárt vonal fölött Claude semmit nem számol. Alatta ember nem ír számot.**

### 4.2 Repo szerkezet

```
hello-reporting/
├── .claude-plugin/
│   └── marketplace.json
├── skills/
│   └── hello-report/
│       ├── SKILL.md                  # a workflow + a varázsló hangneme
│       └── references/
│           ├── export-guide.md       # kattintásvezető, lépésenként
│           ├── report-structure.md   # szekciók, sorrend, mi kerül hova
│           ├── metrics-glossary.md   # metrika-definíciók HU + EN
│           └── narrative-guide.md    # riport-hangnem, szakmai
├── pipeline/
│   ├── parsers/
│   │   ├── zoomsphere.py
│   │   ├── meta_ads.py
│   │   ├── meta_content.py
│   │   ├── meta_daily.py
│   │   └── google_ads.py             # v2 — stub, dokumentált interfésszel
│   ├── detect.py                     # fájl-azonosítás tartalom alapján
│   ├── schema.py
│   ├── join.py
│   ├── kpi.py
│   ├── charts.py
│   ├── images.py                     # letöltés + base64 beágyazás
│   ├── validate.py                   # szám-ellenőrzés a narratívában
│   ├── render.py
│   └── run.py                        # CLI belépési pont
├── templates/
│   ├── report.html.j2
│   ├── brand.css
│   └── print.css
├── clients/
│   └── <ugyfel>/
│       ├── client.yaml
│       └── <YYYY-MM>/
│           ├── input/
│           ├── page_metrics.yaml
│           └── Riport.html
├── tests/
│   ├── fixtures/larus-2026-07/
│   └── test_*.py
└── README.md
```

### 4.3 Telepítés és használat

Telepítés egyszer:

```
/plugin marketplace add hello-agency/hello-reporting
```

Havi futtatás:

```
/hello-report clients/larus/2026-07
```

Csak ellenőrzés, generálás nélkül:

```
/hello-report clients/larus/2026-07 --validate
```

A skill első futáskor ellenőrzi a Python-környezetet és telepíti a függőségeket
(`pandas`, `openpyxl`, `jinja2`, `pyyaml`, `matplotlib`, `pillow`, `requests`).

**Miért plugin és nem másolt skill-mappa:** git-ből frissül. Template-javítás vagy
Meta-oldali oszlopnév-változás javítása mindenkihez eljut újratelepítés nélkül.

---

## 5. Adatmodell

```python
Report
├── meta:      client, period, prev_period, currency, language, generated_at
├── content:                              # ZoomSphere-ből
│   ├── counts:   posts, stories, reels, per_channel
│   └── schedule: napi/heti eloszlás
├── posts: [Post]                         # a join eredménye
├── page:                                 # csatornánként
│   ├── daily:    {metrika: [(dátum, érték)]}
│   ├── totals:   {metrika: összeg}
│   └── manual:   {reach, followers_total}
├── paid:
│   ├── always_on: [Campaign]             # eredménytípus szerint csoportosítva
│   ├── boosted:   [Campaign]             # posztokhoz kötve
│   └── totals:    {spend, reach, impressions, currency}
└── cross:
    ├── avg_reach_organic_post
    ├── avg_reach_boosted_post
    └── boosted_share_of_post_reach

Post
├── zs_row, channel, datetime, type
├── caption, permalink, creative_urls[], creative_b64
├── organic: {reach, views, reactions, comments, shares, clicks, link_clicks}
├── paid:    {spend, reach, impressions, result, result_type} | None
└── is_boosted: bool
```

**Nincs `organic_reach` mező külön a `paid_reach` mellett** posztonként, mert az
`Elérés` teljes elérés — a különbség nem tiszta organikus elérés (átfedés miatt).
A riport `összes elérés` + `ebből fizetett kampány elérése` formában mutatja.

---

## 6. Join-stratégia

| Kapcsolat | Kulcs | Mért találat (Larus, 2026-07) |
|---|---|---|
| ZoomSphere ↔ Tartalom export | poszt ID utótag | **15 / 16** |
| Tartalom export ↔ Meta Ads | caption prefix (30 kar., normalizált) | **4 / 4** |
| ZoomSphere ↔ Meta Ads | caption prefix (30 kar., normalizált) | **8 / 8** (nem nulla költésű) |

Caption-normalizálás: `Bejegyzés:` / `Instagram-bejegyzés:` prefix levágása,
idézőjelek és `…` / `...` eltávolítása, whitespace-összevonás, kisbetűsítés,
majd az **első 30 karakter** prefix-illesztése.

A prefix a csatornát is megadja (`Instagram-bejegyzés:` → IG, `Bejegyzés:` → FB),
így ugyanaz a ZoomSphere-sor két külön hirdetéshez is illeszkedhet — Larusnál a
„Séfünk ajánlata!" poszt FB 15,95 EUR + IG 15,99 EUR.

**Nem illeszkedő boostolt poszt esetén a pipeline felsorolja őket és megáll rákérdezni.
Tippelés nincs.**

---

## 7. A riport szerkezete

Jelölés: 🔒 kódból • ✍️ Claude írja • ⚙️ `client.yaml`-ben kapcsolható

| # | Oldal | Forrás |
|---|---|---|
| 0 | Címlap + „Letöltés PDF-ként" | 🔒 |
| 1 | Tartalomjegyzék | 🔒 |
| 2 | Vezetői összefoglaló | 🔒 szám / ✍️ szöveg |
| 3 | A hónap kulcsmegállapítása | ✍️ |
| 4 | Mit csináltunk (content calendar) | 🔒 |
| 5 | Facebook — oldal | 🔒 |
| 6 | Instagram — profil | 🔒 |
| 7-8 | Top posztok (FB / IG) | 🔒 |
| 9 | Story-k ⚙️ | 🔒 |
| 10 | Paid — always-on kampányok | 🔒 |
| 11 | Paid — boostolt posztok | 🔒 |
| 12 | Organic vs Paid | 🔒 |
| 13 | Mi működött, min javítsunk | ✍️ |
| 14 | Metrika-szótár ⚙️ | 🔒 |
| 15 | Ajánlott KPI-k ⚙️ | 🔒 váz / ✍️ indoklás |
| 16 | Következő lépések | ✍️ |
| 17 | Záró, HELLO kontakt | 🔒 |

### Kiemelt szekciók

**4. „Mit csináltunk"** — egyik benchmarkban sincs. A ZoomSphere content calendarból:
hány poszt, milyen formátumban, milyen ütemben. Ez az ügynökségi munka bizonyítéka,
és megválaszolja a „mit is csináltok" kérdést, mielőtt feltennék.

**12. „Organic vs Paid"** — a riport csúcspontja, csak a hármas joinból áll elő.
Larus 2026-07 példa: organikus poszt átlagos elérése 130, boostolt poszté 4 312
(átlag 14 EUR-ért), a boostolt posztok a havi poszt-elérés 92%-át adják.

**10. és 11. külön** — az always-on kampányok célja lead, a boostolt posztoké láthatóság.
Eltérő `Eredmény jelzése` mellett egy táblában értelmezhetetlenek.

---

## 8. Narratíva-réteg

Claude a lezárt `report_data.json`-t kapja, és négy blokkot ír:
vezetői összefoglaló, kulcsmegállapítás, „mi működött / min javítsunk", következő lépések.

**Hangnem: komoly, szakmai, ügyfélnek kiküldhető.** Konkrét, kerüli az általánosságokat.
Nyelve a `client.yaml`-ben beállított. Részletek: `references/narrative-guide.md`.

**A varázsló hangneme ettől külön kezelendő:** könnyedebb, segítőkész, HELLO-s.
Ez a `SKILL.md`-ben él, és soha nem szivárog át a riportba.

### Szám-ellenőrzés

A `narrative.json` minden számot forrásmező-hivatkozással ad meg:

```json
{
  "block": "executive_summary",
  "text": "A boostolt posztok a havi poszt-elérés {{cross.boosted_share_of_post_reach}}-át adták.",
  "refs": ["cross.boosted_share_of_post_reach"]
}
```

A renderer behelyettesít és ellenőriz. **Ha a szövegben olyan szám szerepel, ami nem
hivatkozásból jön, a build hibát dob.**

---

## 9. Hibakezelés

### Leállító hibák

| Hiba | Detektálás |
|---|---|
| **Eltérő időszak a források között** | minden forrás deklarálja a saját periódusát; eltérésnél stop |
| **Eltérő ügyfél** | `Oldalazonosító` / `Oldal neve` (Tartalom) ↔ `FacebookSources` (ZoomSphere) |
| **Hiányzó kötelező oszlop** | parserenként deklarált kötelező oszloplista; hiánynál megnevezi a fájlt és az oszlopot |
| **Vegyes pénznem** | fejléc-detektálás; több pénznem egy exportban → stop |
| **Nem illeszkedő boostolt poszt** | felsorolás, rákérdezés |
| **Narratíva-szám nem egyezik** | build hiba |

### Nem leállító, de jelzett

- **Hiányzó forrásfájl** → varázsló rákérdez; ha kihagyják, a szekció kimarad,
  és a riport végén módszertani megjegyzés jelzi, mi nem volt mérhető.
  **Hiányzó adat soha nem lesz 0.**
- **Nem letölthető kép** → placeholder + log-figyelmeztetés.
- **Kiszűrt nullás kampánysorok** → darabszám a logban.

### Beépített védelmek

1. **Reach-őr** — nincs kódút, ami napi vagy poszt-szintű reach-et összeadva
   havi reach-nek nevezne. Teszt rögzíti.
2. **Szám-ellenőrzés** a narratívában (lásd 8.).
3. **Hiányzó adat ≠ nulla.**

### Képkezelés

A kreatívok S3/Backblaze URL-jei lejárhatnak, és PDF-nyomtatáskor offline nem töltődnek be.
A build **letölti, méretre csökkenti és base64-ként beágyazza** őket.
A HTML így egyetlen önálló fájl (~3-5 MB, 30 kép mellett), e-mailben küldhető,
és a PDF hibátlan.

---

## 10. PDF export

Elsődleges út: dedikált `print.css` + „Letöltés PDF-ként" gomb, ami `window.print()`-et hív.
Nulla függőség, natív fontok, kattintható linkek megmaradnak.

Másodlagos, opcionális: Playwright-alapú batch script, ha kézi kattintás nélkül
kell PDF több ügyfélre.

---

## 11. Konfiguráció (`client.yaml`)

```yaml
client:
  name: "Larus Étterem"
  fb_page_id: "100064824963030"
  fb_page_name: "Larus Étterem"
  ig_handle: "larusetterem"

report:
  language: hu          # hu | en
  currency: EUR         # az exportból detektált érték ellenőrzésére
  kpis:                 # a kiemelt mérőszámok, varázslóban választva
    - reach
    - link_clicks
    - interactions
    - spend
    - cost_per_result
  sections:
    stories: true
    metrics_glossary: true
    recommended_kpis: true
    google_ads: false   # v2

carryover:              # az előző riport zárószámai
  followers_fb: 34600
  followers_ig: 4900
```

A varázsló első futáskor létrehozza, később csak a hiányzó mezőkre kérdez rá.

---

## 12. Tesztelés

A 2026 júliusi Larus-anyag teljes valós tesztkészlet: ZoomSphere XLSX + Ads CSV +
Tartalom CSV + 8 napi insights CSV. Ez lesz a `tests/fixtures/larus-2026-07/`,
mellette *golden file*-ként a helyesnek elfogadott `report_data.json`.

| Teszt | Mit rögzít |
|---|---|
| Parser — kódolás | UTF-16 BOM felismerés, `sep=,` sor kezelése |
| Parser — azonosítás | metrika a 2. sorból, nem fájlnévből |
| Parser — pénznem | `Elköltött összeg (EUR)` → EUR; HUF-os változat is |
| Parser — zajszűrés | 31 sorból 18 nullás kiesik, a darabszám logolva |
| Join | 15/16, 4/4, 8/8 — rögzített értékek |
| Eredménytípus | eltérő `Eredmény jelzése` nem adódik össze |
| Reach-őr | napi/poszt reach összegzése havi reach-ként → hiba |
| Narratíva | nem hivatkozott szám a szövegben → build hiba |
| Ügyfél-keresztellenőrzés | idegen `Oldalazonosító` → stop |
| Végigfutás | teljes pipeline → HTML renderel, nincs üres szekció |

---

## 13. Nyitott kérdések

| # | Kérdés | Hatás | Mikor dől el |
|---|---|---|---|
| 1 | Van-e a Tartalom fülön tartalomtípus-szűrő, amiben szerepel a Történetek? | ha igen, a story-teljesítmény bekerül a v1-be | implementáció előtt, egy ellenőrzéssel |
| 2 | Van-e organic/paid szűrő az Eredmények csempéknél? | ha igen, a page-szintű számok tisztán organikusak lehetnek | implementáció előtt |
| 3 | Az IG Tartalom export oszlopai megegyeznek a FB-ével? | a `meta_content.py` egy vagy két változatot kezel | első IG export beérkezésekor |
| 4 | HUF-os ügyfél Ads exportja | pénznem-detektálás tesztelése | Mammut-export beérkezésekor |

Egyik sem blokkolja az implementáció megkezdését — a parserek és a pipeline
felépíthetők a meglévő valós adatokon, és ezek mindegyike hozzáadás, nem átépítés.

---

## 14. Verziók

**v1** — ez a spec.

**v2** — Google Ads modul. A szekció-architektúra „ha van adat, van szekció" logikája
és a `google_ads.py` stub már készen áll; egy parser és egy riport-szekció hozzáadása.

**v3** — MCP / Graph API integráció. Csak az ① parser-réteg cserélődik;
a normalizálás, a join, a KPI-számítás és a renderelés változatlan marad.
Ekkor a manuális export-lépés és a varázsló nagy része kiváltható.
