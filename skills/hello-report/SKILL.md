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

### 1. Nézd meg, mi van a mappában

```bash
python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM> --validate
```

Ez kiírja, mit talált és mi hiányzik. Ha hibával áll meg, olvasd el az üzenetet —
megnevezi a fájlt és a problémát.

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

Ha a build `NarrativeError`-t dob, az üzenet megmondja, melyik számot írtad le
vagy melyik mező nem létezik. Javítsd, ne kerüld meg.

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
├── client.yaml                # ügyfélnév, oldal-azonosítók, nyelv, pénznem
└── <YYYY-MM>/
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
