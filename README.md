# HELLO Reporting

Havi social media riport a Meta és a ZoomSphere exportjaiból — egy paranccsal,
ügyfélnek kiküldhető formában.

A kimenet egyetlen HTML fájl: 21 oldal, 16:9, HELLO-brandelt, valódi
kreatívokkal. E-mailben küldhető, offline megnyitható, egy kattintással PDF.

## Telepítés

Claude Code-ban, egyszer:

```
/plugin marketplace add Hello-agency-hun/hello-social-riport
```

## Havi használat

```
/hello-report clients/larus/2026-07
```

Claude végigvezet: megnézi, mi van a mappában, és ha valami hiányzik, megmondja
pontosan hol találod. Ha minden megvan, megírja a riportot.

## Mit kell letöltened

Ügyfelenként ~6 perc, hónaponként egyszer. A részletes kattintásvezetőt Claude
elővezeti, ha hiányzik valami — de röviden:

| Honnan | Mit |
|---|---|
| ZoomSphere | Scheduler export a hónapra |
| Meta Ads Manager | kampány-export a hónapra |
| Business Suite → Tartalom | külön Facebookra és Instagramra |
| Business Suite → Eredmények | csempénként, csatornánként öt-öt CSV |

**Ne nevezd át a fájlokat.** A rendszer a tartalmukból ismeri fel őket, nem a
nevükből — a `Felkeresések.csv` és a `Felkeresések-2.csv` ütközése rendben van.

Amit a Meta nem exportál (havi elérés, követőszám), az a riportban szaggatott
kerettel megjelenik, és beírhatod a böngészőben.

## Amit a riportban csinálhatsz

- **Letöltés PDF-ként** — jobb felső gomb
- **Számok beírása** — a szaggatott keretű mezőkbe
- **Szöveg átírása** — kattints bele bármelyik narratíva-blokkba
- **Megjegyzés** — bármelyik oldal jobb alsó sarkában
- **Mentés** — egyetlen `review.json` letöltődik; tedd a hónap mappájába, és
  szólj Claude-nak, hogy alkalmazza

Az üres mezők, a szerkesztő-keretek és a megjegyzés-gombok **nyomtatásban nem
látszanak** — az ügyfélhez tiszta dokumentum megy.

## Mappaszerkezet

```
clients/larus/
└── 2026-07/
    ├── client.yaml        # ügyfélnév, oldal-azonosítók, nyelv, pénznem
    ├── input/             # ide dobd az exportokat
    ├── review.json        # amit a böngészőben mentettél
    ├── previous.json      # opcionális: az előző havi report_data.json
    ├── report_data.json   # generált
    └── Riport.html        # generált
```

## Az elv

**Minden szám kódból jön, és visszavezethető egy forrásfájlra.**

A riport szövegét nyelvi modell írja, de **számot nem írhat le** — csak
hivatkozni tud rá (`{cross.reach_multiplier|x}`), amit a rendszer helyettesít be.
A leírt számot a build elutasítja. Ez nem óvatosság: ez teszi lehetetlenné, hogy
egy tetszetős, de hamis szám kikerüljön az ügyfélhez.

Amit nem lehet mérni, azt nem találjuk ki. A havi elérés például
**matematikailag nem számítható** napi értékek összegéből — aki két napon is
látott minket, egy ember —, ezért azt beírod, nem kitaláljuk.

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
python tools/vendor_fonts.py                    # Open Sauce One → woff2
python tools/extract_logo.py "<brand guide.pdf>"  # logó → SVG
python tools/import_previous.py "<riport.pdf>"    # előző havi számok, javaslatként
python tools/build_styleguide.py                  # design rendszer dokumentum
```

A design rendszer élő referenciája:
`skills/hello-report/references/design-system.html` — nyisd meg böngészőben.
Generált a `brand.css`-ből és a `charts.py`-ból, tehát nem tud elcsúszni tőlük.

Tervek és döntések: `docs/superpowers/`.
