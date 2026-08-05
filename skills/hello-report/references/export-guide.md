# Exportok letöltése

Ezt a dokumentumot csak akkor töltsd be, ha a `--validate` hiányzó fájlt jelez.
Ha minden megvan, felesleges kontextus.

**Vezesd végig a menedzsert lépésenként, visszaigazolást várva.** Ne másold be
az egész listát egyszerre — csak azt a lépést, ami éppen hiányzik.

Minden fájl az `input/` mappába megy, **átnevezés nélkül**. A parser tartalom
alapján ismeri fel őket, nem fájlnév alapján.

---

## 1. ZoomSphere — tartalomnaptár

*Ismerős lépés, elég egy emlékeztető.*

ZoomSphere → **Social media Scheduler** → a hónap kijelölése → **Export**.

Fájl: `export_<ügyfél> Social media Scheduler_<dátum>.xlsx`

Ez adja a posztok szövegét, a kreatívokat, a linkeket és a poszt-azonosítókat.
Metrikát nem tartalmaz — az a Metából jön.

## 2. Meta Ads Manager — kampányok

*Ismerős lépés, elég egy emlékeztető.*

Hirdetéskezelő → **Kampányok** → időszak a riportált hónapra → **Exportálás** →
a szokásos oszlopsablonnal.

Fájl: `<ügyfél>-Kampányok-<dátum>.csv`

## 3. Meta Business Suite — Tartalom (Facebook)

Ez adja a poszt-szintű elérést és interakciókat. **Enélkül nincs top-poszt oldal.**

1. Business Suite → **Statisztika**
2. Bal oldali menü → **Tartalom**
3. Fent az időszak a riportált hónapra
4. Jobb felül **Exportálás** → CSV

Fájl: `<dátumtartomány>_<oldalazonosító>.csv`

## 4. Meta Business Suite — Tartalom (Instagram)

Ugyanez, de **előbb váltani kell a fiókot**:

1. Bal felül a fiókváltóval válts az Instagram-fiókra
2. Statisztika → Tartalom → Exportálás

Ha ez hiányzik, a riport Instagram-szekciója a boostolt posztokat mutatja
kreatívval és költéssel, de organikus elérés nélkül. Működik, csak kevesebbet mond.

## 5. Meta Business Suite — Eredmények, Facebook

Statisztika → **Eredmények**. Minden csempénél külön exportálás, összesen öt:

- Facebook-felkeresések
- Facebook-követések
- Tartalomnál végzett műveletek
- Facebookos hivatkozáskattintások
- Megtekintések

Mindegyik egy külön CSV. **A fájlnevek ütközni fognak** (`Felkeresések.csv`,
`Felkeresések-2.csv`) — ez rendben van, ne nevezd át őket. A parser a fájl
belsejéből tudja, melyik metrika.

## 6. Meta Business Suite — Eredmények, Instagram

Ugyanaz a fiókváltás után, öt csempe:

- Instagram-profilfelkeresések
- Instagram-követések
- Interakció tartalmaknál
- Instagramos hivatkozáskattintások
- Megtekintések

## 7. Havi elérés és követőszám

**Ezeket nem kell letölteni** — a riportban ott lesz a helyük szaggatott kerettel.

Statisztika → **Elérés** csempe, az időszak a riportált hónapra állítva.
Csatornánként egy szám. Ugyanígy a követő-összlétszám a Közönség alatt.

A menedzser beírja a riportba, megnyomja a **Mentés** gombot, és a letöltött
`review.json`-t a hónap mappájába teszi. A következő hónaptól a követőszám már
automatikus, mert az előző riportból jön.

## 8. Előző hónap (opcionális)

Az összehasonlító oldalakhoz. Két út:

- **Egyszerű:** az előző havi `report_data.json` átmásolva `previous.json` néven.
- **Első hónapban:** a korábbi riport PDF-jéből javaslat kérhető:

  ```bash
  python tools/import_previous.py "<előző riport.pdf>"
  ```

  Ez **nem ír fájlt** — javaslatot nyomtat. A számok kerekítettek lehetnek
  (`149.3K` → 149 300), és idegen elrendezésnél félrecsúszhatnak, ezért a
  menedzsernek össze kell vetnie a PDF-fel, mielőtt beírja.

---

## Ha valami nem stimmel

| Hibaüzenet | Mit jelent |
|---|---|
| `a forrás időszaka … a riportált hónap …` | rossz hónap exportja került a mappába |
| `Más ügyfél adata került a mappába` | két ügyfél fájljai keveredtek |
| `két ZoomSphere export van a mappában` | újraletöltésnél bennmaradt a régi — töröld |
| `ismeretlen napi metrika` | új Meta-csempe; a `client.yaml` `daily_metric_overrides` szakaszába kell felvenni |
| `csonka napi export` | a letöltés félbeszakadt — töltsd le újra |
