---
name: hello-report
description: >
  Havi social media riport összeállítása egy ügyfélnek a Meta és a ZoomSphere
  exportjaiból. Használd, amikor a felhasználó riportot kér egy ügyfélre és egy
  hónapra, a `clients/<ugyfel>/<YYYY-MM>` mappára hivatkozik, vagy exportfájlokat
  dob be feldolgozásra.
---

# HELLO havi social riport

Ez a skill a HELLO Agency social media menedzsereinek készült. Egy hónap
exportjaiból összeállít egy ügyfélnek kiküldhető, brandelt HTML riportot,
amit a böngészőből PDF-be lehet nyomtatni.

## A hangnem

**Veled, a menedzserrel könnyed és segítőkész vagyok** — ez itt egy közös munka,
nem egy hivatalos eljárás. Ha hiányzik valami, elmondom hova kell kattintani,
nem szemrehányást teszek.

**A riport hangneme ettől külön él, és komoly** — azt az ügyfél kapja meg.
Arról a `references/narrative-guide.md` szól; ez a kettő soha nem keveredik.

## A szabály, amit nem lehet megkerülni

Minden szám a kódból jön, és visszavezethető egy forrásfájlra. Én a narratívát
írom — és **abban egyetlen számot sem szabad leírnom**. Számra csak hivatkozni
lehet: `{cross.reach_multiplier|x}`, amit a renderer helyettesít be.

A build elutasít minden leírt számjegyet. Ez nem bosszantás, hanem az egyetlen
biztosíték arra, hogy egy tetszetős, de hamis szám ne kerüljön ki az ügyfélhez.

## A menete

### 0. Előbb kérdezz, csak utána dolgozz

**Ne kezdj el riportot építeni addig, amíg a menedzser fel nem töltötte a
fájlokat.** Ha valaki azt mondja, hogy „csinálj riportot a Larusnak júliusra",
az nem azt jelenti, hogy keress adatot valahol a repóban — azt jelenti, hogy
*most kezdjük el együtt*.

A sorrend:

1. **Kérdezd meg az ügyfél nevét és a hónapot**, ha nem egyértelmű.
2. **Hozd létre a mappát**: `clients/<ugyfel>/<YYYY-MM>/input/`, és **mondd meg
   a pontos útvonalat**.
3. **Add oda a checklistet, szó szerint** — ne prózát:

   ```bash
   python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM> --checklist
   ```

   Ez konfiguráció nélkül is fut, és a `client.yaml`-ből szűkül, ha már van.
   **Másold be a kimenetét egy az egyben.** A menedzser nem olvas el négy
   bekezdést, mielőtt letölt — kipipál. A Mammut-próbán öt kör oda-vissza lett
   abból, hogy prózát kapott: a Tartalom exportok kimaradtak, a ZoomSphere
   PDF-ként jött, az Ads XLSX-ként.

   Az `references/export-guide.md`-t csak akkor töltsd be, ha valamelyik
   ponthoz külön magyarázat kell.
4. **Várj.** Ne találgass, ne építs félkész adatból.
5. Amikor szól, hogy kész, indulhat az 1. lépés.

> **A `tests/fixtures/` NEM adatforrás.** Valódi ügyféladat van benne, teljes
> exportkészlettel és kész narratívával — pontosan úgy néz ki, mint egy éles
> munkamappa. Riportot soha nem ebből készítünk: a `--validate` és a build
> el is utasítja. Ez a tesztek anyaga.

### 1. Nézd meg, mi van a mappában

```bash
python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM> --validate
```

Ez kiírja, mit talált, és külön szakaszban azt, **mi hiányzik és mibe kerül**:

```
Hiányzó források:
  ✗ Instagram Tartalom export — enélkül nincs poszt-szintű elérés
```

Ha hibával áll meg, olvasd el az üzenetet — megnevezi a fájlt és a problémát.
Üres mappánál nem készít nullákkal teli riportot, hanem megáll.

A hiányt a `client.yaml` alapján állapítja meg: csak arról a csatornáról
hiányol adatot, amiről a konfiguráció szerint van fiók.

### 1b. Ha képernyőképeket is feltöltött

A `--validate` így szól:

```
📷 2 képernyőkép van a mappában:
  · business-suite-eleres.jpg
  → Olvasd ki belőlük, ami hiányzik, MIELŐTT bármit megkérdeznél.
```

**Nézd meg őket.** A menedzser nem véletlenül tette be: a Business Suite
csempéin ott a havi elérés, a követőszám és az előző hónaphoz mért változás.
Ami ezekről leolvasható, azt **ne kérdezd meg tőle még egyszer** — írd be a
`client.yaml`-be, és mondd meg neki, mit olvastál ki, hogy ellenőrizhesse.

Ha a kép alapján bizonytalan vagy egy számban, azt kérdezd meg — de csak azt.

### 1c. Ha rossz formátumú fájl került be

```
HIBA: nem a várt formátumban van néhány fájl:
  · zoomsphere-export.pdf — PDF. Ha ez a ZoomSphere-export, töltsd le XLSX-ként…
```

Ne állj meg ennél. **Nézd meg a fájlt**: a PDF-ből és a régi Excelből ki tudod
nyerni a táblázatot, és menteni CSV-ként az `input/` mappába. Utána töröld az
eredetit, hogy ne ütközzön.

Ha az átalakítás bizonytalan — mert a PDF elrontott táblázatot tartalmaz —,
akkor kérd meg, hogy töltse le újra. De előbb próbáld meg.

### 2. Ha hiányzik forrásfájl

Töltsd be a `references/export-guide.md`-t, és vezesd végig a menedzsert
**lépésenként, visszaigazolást várva**. Ne öntsd rá az egészet egyszerre.

**Ha minden fájl megvan, ezt a dokumentumot ne is töltsd be** — felesleges
kontextus.

### 3. Építsd meg a riportadatot

```bash
python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM>
```

Ez létrehozza a `report_data.json`-t és a `Riport.html`-t. Olvasd el a
`report_data.json`-t — ez az egyetlen forrásod a narratívához.

### 4. Írd meg a narratívát

Olvasd el a `references/narrative-guide.md`-t, és írd meg a
`clients/<ugyfel>/<YYYY-MM>/narrative.json`-t.

Öt blokk: `executive_summary`, `key_finding` (`title` + `body`), `what_worked`,
`what_to_improve`, `next_steps`.

**A riport nyelvén írd**, amit a `client.yaml` `report.language` mezője mond —
nem azon, amin a menedzserrel beszélgetsz. Ha ott `en` áll, az egész narratíva
angol. A build ezt ellenőrzi. A poszt-szövegeket viszont nem fordítjuk: azok az
ügyfél saját tartalmai.

Ha a build `NarrativeError`-t dob, az üzenet megmondja, melyik számot írtad le
vagy melyik mező nem létezik. Javítsd, ne kerüld meg.

**Ha új szekciót vagy layoutot tervezel:** előbb nézd meg a
`references/design-system.html`-t. Generált dokumentum a valódi `brand.css`-ből
és `charts.py`-ból, tehát nem tud elcsúszni a rendszertől. Másolható
markup-mintákat tartalmaz minden komponensre, és mellettük a szabályt, hogy
miért úgy — köztük azokat, amiket hibából tanultunk (miért kell a `.fill` burok,
miért az `li`-n legyen a betűméret, miért nem szabad `cover`-rel vágni a
kreatívot).

### 5. Rendereld újra, és add oda

Futtasd újra a 3. lépést, majd mondd meg a menedzsernek, hol a `Riport.html`,
és hogy:

- a jobb felső gombbal PDF-be nyomtathatja,
- a szaggatott keretű mezőkbe beírhatja azt, amit a Meta nem exportál,
- bármelyik szövegblokkba belekattinthat és átírhatja,
- bármelyik oldalhoz megjegyzést fűzhet,
- a **Mentés** gomb egyetlen `review.json`-t tölt le, amit a hónap mappájába kell tennie.

### 6. Ha visszajön review.json-nal

```bash
python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM> --apply-review
```

A szövegjavítások bekerülnek a `narrative.json`-be, a megjegyzések pedig
**kiíródnak a konzolra**. Azokat neked kell feldolgoznod: ha strukturális
kérést tartalmaznak („ide kérek egy kördiagramot"), a `references/` és a
`templates/` keretein belül hajtsd végre — vagy mondd meg, miért nem megy.

## Mappaszerkezet

```
clients/<ugyfel>/
└── <YYYY-MM>/
    ├── client.yaml            # ügyfélnév, oldal-azonosítók, nyelv, pénznem
    ├── input/                 # ide kerülnek az exportok, átnevezés nélkül
    ├── narrative.json         # amit én írok
    ├── review.json            # amit a menedzser visszaküld
    ├── previous.json          # opcionális: az előző havi report_data.json
    ├── report_data.json       # generált
    └── Riport.html            # generált
```

## Amit soha ne csinálj

- **Ne írj számot a narratívába.** A build úgyis elutasítja, de a lényeg nem
  az elutasítás — hanem hogy ne is próbáld meg.
- **Ne becsülj meg hiányzó adatot.** Ha valami nincs, az a riportban vagy
  kitölthető mezőként jelenik meg, vagy kimarad. Nem találjuk ki.
- **Ne írd a riportba, mit nem tudunk mérni.** A hiánylistát a `--validate`
  mutatja, a menedzsernek. Az ügyfél azt kapja meg, amit csináltunk.
- **Ne nevezd át a bemeneti fájlokat.** A parser tartalom alapján ismeri fel őket.
