# HELLO Reporting — agent-útmutató

Ez a repó egy havi social media riportot állít elő a Meta és a ZoomSphere
exportjaiból. Ha téged egy HELLO-menedzser kért meg riportra, ez a te
munkaleírásod.

**Az érdemi eljárás a [`skills/hello-report/SKILL.md`](skills/hello-report/SKILL.md)
fájlban van. Olvasd el, mielőtt bármihez hozzáérsz.** Ez a fájl csak
odairányít, és azt teszi hozzá, ami platformonként eltér — szándékosan nem
másolja meg a tartalmát. A repó már megbüntetett egyszer a duplikációért: a
mappaábra két helyen szerepelt, és az egyik rossz helyre tette a
`client.yaml`-t.

## Mielőtt bármit csinálnál

**Ne kezdj el riportot építeni addig, amíg a menedzser fel nem töltötte a
fájlokat.** A „csinálj riportot a Larusnak júliusra” nem azt jelenti, hogy
keress adatot a repóban — azt jelenti, hogy *most kezdjük el együtt*.

Kérdezd meg az ügyfél nevét és a hónapot, hozd létre a
`clients/<ugyfel>/<YYYY-MM>/input/` mappát, mondd meg a pontos útvonalat, kérd
meg, hogy oda töltse fel az exportokat átnevezés nélkül — **és várj**.

**A `tests/fixtures/` nem adatforrás.** Valódi ügyféladat van benne, teljes
exportkészlettel és kész narratívával, tehát pontosan úgy néz ki, mint egy éles
munkamappa. A CLI el is utasítja, ha onnan próbálsz építeni.

## Ami az input mappában lesz, azon túl, amit kértél

**Képernyőképek.** A menedzser gyakran bedobja a Business Suite csempéiről
készült képeket is. Ezek nem szemét: rajtuk van a havi elérés, a követőszám és
az előző hónaphoz mért változás. A `--validate` felsorolja őket. **Nézd meg
őket, mielőtt bármit megkérdeznél** — amit onnan le lehet olvasni, azt ne kérd
el újra. Írd be a `client.yaml`-be, és mondd meg, mit olvastál ki.

**Rossz formátum.** Ha PDF vagy régi `.xls` kerül be, a build megnevezi.
Ne állj meg ennél: nyisd meg, nyerd ki belőle a táblázatot, mentsd CSV-ként az
`input/` mappába, és töröld az eredetit. Csak akkor kérj újratöltést, ha az
átalakítás bizonytalan.

## A három szabály, amit sosem szabad megkerülni

Ezeket a kód is kikényszeríti — nem emlékezetből kell tartanod őket —, de
tudnod kell róluk, mert különben a hibaüzenetek értelmetlennek látszanak.

1. **A narratívába nem írhatsz számot.** Számra csak hivatkozni lehet:
   `{cross.reach_multiplier|x}`. A build minden leírt számjegyet elutasít. Ez
   teszi lehetetlenné, hogy egy tetszetős, de hamis szám kikerüljön az
   ügyfélhez.
2. **Hiányzó adatot nem becsülsz meg.** Ha valami nincs, azt a `--validate`
   megnevezi, és megmondja, honnan szerezhető be.
3. **A bemeneti fájlokat nem nevezed át.** A parser a tartalmukból ismeri fel
   őket, nem a nevükből.

## Telepítés

```bash
git clone https://github.com/Hello-agency-hun/hello-social-riport.git
cd hello-social-riport
pip install -e ".[dev]"
pytest -q
```

## A parancs

```bash
python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM> --validate
```

A `--validate` nélkül elkészül a `report_data.json` és a `Riport.html` is.

### Homokozóban: `--offline`

Ha a környezeted nem enged hálózatot — a Codex sandbox alapból ilyen —, a
kreatívok letöltése hibára fut. Ilyenkor:

```bash
python -m pipeline.cli clients/<ugyfel>/<YYYY-MM> --period <YYYY-MM> --offline
```

A számok és a szöveg ugyanazok lesznek, a képek helyén helyőrző áll. **Az
ügyfélnek kiküldendő riportot ne így készítsd** — ahhoz kell a hálózat, mert a
kreatívok nélkül a riport fele hiányzik.

## Amit mikor olvass el

Ne told be az egészet előre. Mindegyik akkor kell, amikor ott tartasz:

| fájl | mikor |
|---|---|
| [`SKILL.md`](skills/hello-report/SKILL.md) | mindig, elsőként |
| [`references/export-guide.md`](skills/hello-report/references/export-guide.md) | ha a `--validate` hiányzó forrást jelez |
| [`references/narrative-guide.md`](skills/hello-report/references/narrative-guide.md) | mielőtt a `narrative.json`-t írod |
| [`references/metrics-glossary.md`](skills/hello-report/references/metrics-glossary.md) | ha egy metrika jelentése nem egyértelmű |
| [`references/design-system.html`](skills/hello-report/references/design-system.html) | ha új szekciót vagy layoutot tervezel — nyisd meg böngészőben |

A `design-system.html` generált dokumentum a valódi `brand.css`-ből és
`charts.py`-ból, tehát nem tud elcsúszni a rendszertől. Ha módosítod
valamelyiket, futtasd újra: `python tools/build_styleguide.py`.

## Platformkülönbségek

Ez a repó Claude Code plugin-ként és sima git-repóként is működik. A különbség
csak a belépési pont:

| | Claude Code | Codex és más agentek |
|---|---|---|
| telepítés | `/plugin marketplace add …` | `git clone` |
| indítás | `/hello-report clients/…` | prózában kéred |
| ez az útmutató | `SKILL.md` (automatikus) | `AGENTS.md` (automatikus) |
| referenciák | igény szerint betöltve | igény szerint beolvasva |

A `pipeline/`, a `templates/` és a `tools/` mindkét helyen ugyanaz. **A
biztosítékok is:** a számjegy-tiltás, a duplikátum-őr és az időszak-ellenőrzés
a kódban van, nem a promptban — akármelyik modell írja a szöveget, a build
ugyanúgy elutasítja a hibát.

## Tesztek

```bash
pytest -q
```

A tesztek a valós Larus 2026-07 export-készleten futnak
(`tests/fixtures/larus-2026-07/`), golden file-hoz kötve. Ha a
`report_data.json` szerkezetét módosítod, a golden file-t újra kell generálni —
a `tests/test_cli.py::test_output_matches_the_golden_file` ezt fogja jelezni.

A fixture bájtpontos másolat a menedzser valódi letöltéseiről; a
`.gitattributes` védi a sorvég-konverziótól. **Ne szerkeszd.**
