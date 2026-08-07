# HELLO Reporting

Havi social media riport a Meta és a ZoomSphere exportjaiból — ügyfélnek
kiküldhető formában, körülbelül húsz perc alatt.

A kimenet egyetlen HTML fájl: 22 oldal, 16:9, HELLO-brandelt, valódi
kreatívokkal. E-mailben küldhető, offline megnyitható, egy kattintással PDF.

---

## Mire jó, és mire nem

**Jó arra**, hogy a letöltött exportokból összeálljon egy riport, amiben minden
szám visszavezethető egy forrásfájlra, és a szöveg a te szavaiddal íródik.

**Nem jó arra**, hogy kitalálja, ami nincs meg. Amit a Meta nem exportál, azt
vagy tőled kéri be, vagy szaggatott keretű mezőként meghagyja a riportban —
de nem becsüli meg.

---

## 1. Telepítés — egyszer, összesen

### Claude Code-ban

```
/plugin marketplace add Hello-agency-hun/hello-social-riport
```

Ennyi. Nem kell se Python-tudás, se parancssor — a továbbiakban Claude-dal
beszélgetsz, ő futtatja a parancsokat.

### Codexben vagy más agentben

```bash
git clone https://github.com/Hello-agency-hun/hello-social-riport.git
cd hello-social-riport && pip install -e .
```

Az agent az `AGENTS.md`-ből magától megtudja, mi a dolga. Nincs
`/hello-report` parancs — prózában kéred: *„csinálj riportot a Larusnak
júliusra"*.

Egy különbség: ha az agent hálózat nélküli homokozóban fut (a Codex alapból
ilyen), a kreatívok nem töltődnek le. A számok és a szöveg ugyanazok, a képek
helyén helyőrző áll. Az ügyfélnek kiküldendő riporthoz engedd a hálózatot.

---

## 2. Új ügyfél beállítása — ügyfelenként egyszer

Mondd Claude-nak:

> Csinálj riportot a Larusnak 2026 júliusra.

Ő létrehozza a mappát, és elkéri, amit tudnia kell. **Két dolgot fog kérdezni**,
amit nem tud kiolvasni a fájlokból:

| Amit kérdez | Honnan veszed |
|---|---|
| Az ügyfél neve, ahogy a címlapon szerepeljen | te tudod |
| A követőszám Facebookon és Instagramon | a profil fejlécéből, fél perc |

Az **oldalazonosítót és az oldal nevét nem kérdezi** — azok benne vannak a
Tartalom exportban, kiolvassa őket.

> **Miért kell a követőszám előre?**
> Mert a Meta nem exportálja, viszont enélkül nem lehet megmondani, mennyit
> nőtt a közönség. Korábban a riport végén állt kitölthető mezőként, és pont
> ezért maradt mindig üresen — oda már senki nem ment vissza.

---

## 3. Amit le kell töltened — ügyfelenként ~6 perc havonta

Négy helyről jön adat. Ha valamelyik hiányzik, Claude megmondja, **melyik és
mibe kerül** — nem kell fejből tudnod.

### a) ZoomSphere

Scheduler → export a hónapra → `.xlsx`

Ebből jön a **poszt-szöveg és a kreatív** (kép, videó-thumbnail). Enélkül a
riportban nincs mit megmutatni.

### b) Meta Ads Manager

Kampányok fül → állítsd be a hónapot → Exportálás → `.csv`

Ebből jön a **költés, a boostok és a kampányeredmények**.

### c) Business Suite → Tartalom

Külön a **Facebookra** és külön az **Instagramra**. Állítsd be a hónapot,
és exportáld.

Ebből jön a **poszt-szintű elérés**. Ez a legfontosabb fájl: enélkül tudjuk,
hogy volt poszt, de nem tudjuk, hányan látták.

### d) Business Suite → Eredmények

Csempénként külön CSV, **csatornánként öt-öt**:

- Felkeresések
- Hivatkozáskattintások
- Interakciók
- Követők
- Megtekintések

Ebből jönnek a **napi görbék** és az oldal havi összesítései.

### ⚠️ Ne nevezd át a fájlokat

A rendszer a **tartalmukból** ismeri fel őket, nem a nevükből. A
`Felkeresések.csv` és a `Felkeresések-2.csv` ütközése rendben van — az egyik a
Facebook, a másik az Instagram, és ezt a fájl belsejéből tudja.

Ha átnevezed, attól még működik. De ha **szerkeszted** (megnyitod Excelben és
mented), akkor elromolhat.

### Hova tedd őket

Mind egy mappába:

```
clients/<ügyfél>/<év-hónap>/input/
```

Claude megmondja a pontos útvonalat. Bedobod, szólsz, és megy tovább.

---

## 4. A riport elkészítése

Innentől Claude dolgozik:

1. **Megnézi, mi van a mappában.** Ha hiányzik valami, megnevezi, és megmondja,
   hol találod. Ha kakukktojás került be, azt is szól — nem hagyja figyelmen
   kívül, mert lehet, hogy mégis riportadat volt.
2. **Kiszámolja a számokat.** Ez a rész kódból megy, nem nyelvi modellből.
3. **Megírja a szöveget** — vezetői összefoglaló, kulcsmegállapítás, mi
   működött, min javítsunk, következő lépések.
4. **Megépíti a riportot.** Kapsz egy `Riport.html`-t.

---

## 5. Amit a riportban csinálhatsz

Nyisd meg böngészőben (dupla kattintás a fájlra).

| Amit szeretnél | Hogyan |
|---|---|
| **PDF** | jobb felső gomb: *Letöltés PDF-ként* |
| **Szám beírása** | kattints a szaggatott keretű mezőbe |
| **Szöveg átírása** | kattints bele bármelyik szövegblokkba |
| **Megjegyzés** | bármelyik oldal jobb alsó sarkában |
| **Mentés** | *Mentés a mappába* gomb |

### A mentésről

Az első mentésnél a böngésző megkérdezi, hova tegye — válaszd a hónap
mappáját, `review.json` néven. **Utána minden mentés automatikusan oda megy.**

Ha megvagy, csak annyit mondj Claude-nak:

> Mentettem.

Ő átveszi a javításaidat, újraépíti a riportot, és átnézi, mi változott. Nem
kell fájlt küldözgetni, se ide-oda ugrálni a chat és a böngésző között.

*(Ha a böngésződ nem támogatja a közvetlen mentést, a **Mentés** gomb letölti a
`review.json`-t — azt kézzel kell a hónap mappájába másolni.)*

### Amit az ügyfél nem lát

A szaggatott keretek, a szerkesztő-jelölések és a megjegyzés-gombok
**nyomtatásban eltűnnek**. Az ügyfélhez tiszta dokumentum megy.

---

## 6. Ha hibaüzenetet kapsz

Minden hibaüzenet megmondja, **mi a baj és mit tegyél**. A leggyakoribbak:

| Üzenet | Mi történt |
|---|---|
| *nincs client.yaml* | új ügyfél — az üzenet tartalmazza a kitöltött sablont |
| *hiányzik a követőszám* | írd be a profilról leolvasott számot |
| *nem azonosítható fájl* | valami idegen került az `input` mappába |
| *két … export van a mappában* | a régit töröld, különben az adat megkétszereződne |
| *a csempe nem árulja el, melyik csatornáé* | az üzenet ad egy kimásolható sort |

Ha elakadsz, másold be az üzenetet a chatbe.

---

## Mappaszerkezet

```
clients/larus/
└── 2026-07/
    ├── client.yaml        # ügyfélnév, azonosítók, követőszám, pénznem
    ├── input/             # ide dobd az exportokat
    ├── review.json        # amit a böngészőben mentettél
    ├── previous.json      # opcionális: az előző havi report_data.json
    ├── narrative.json     # a riport szövege
    ├── report_data.json   # generált — minden szám
    └── Riport.html        # generált — a kész riport
```

---

## Az elv, ami miatt megbízhatsz benne

**Minden szám kódból jön, és visszavezethető egy forrásfájlra.**

A riport szövegét nyelvi modell írja, de **számot nem írhat le** — csak
hivatkozni tud rá (`{cross.reach_multiplier|x}`), amit a rendszer helyettesít
be. A leírt számot a build elutasítja.

Ez nem óvatoskodás: ez teszi **lehetetlenné**, hogy egy tetszetős, de hamis
szám kikerüljön az ügyfélhez.

Ugyanez a másik irányba is igaz. A havi elérés például **matematikailag nem
számítható** napi értékek összegéből — aki két napon is látott minket, egy
ember. Ezért azt beírod, nem kitaláljuk.

---

## Fejlesztőknek

```bash
pip install -e ".[dev]"
pytest -q
```

A tesztek a valós Larus 2026-07 export-készleten futnak
(`tests/fixtures/larus-2026-07/`), golden file-hoz kötve. A fixture bájtpontos
másolat — a `.gitattributes` védi a sorvég-konverziótól.

Egyszeri eszközök, az eredményük commitolva:

```bash
python tools/vendor_fonts.py                      # Open Sauce One → woff2
python tools/extract_logo.py "<brand guide.pdf>"  # logó → SVG
python tools/import_previous.py "<riport.pdf>"    # előző havi számok, javaslatként
python tools/build_styleguide.py                  # design rendszer dokumentum
```

Az agentek belépési pontjai: `skills/hello-report/SKILL.md` (Claude Code) és
`AGENTS.md` (Codex és társai). Az utóbbi **útvonaljelző, nem második leírás** —
a `tests/test_agent_docs.py` őrzi, hogy ne hízzon párhuzamos eljárássá, és hogy
minden hivatkozott fájl létezzen.

A design rendszer élő referenciája:
`skills/hello-report/references/design-system.html` — nyisd meg böngészőben.
Generált a `brand.css`-ből és a `charts.py`-ból, tehát nem tud elcsúszni tőlük.

Tervek és döntések: `docs/superpowers/`.
