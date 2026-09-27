# Exportok letöltése

Ezt a dokumentumot csak akkor töltsd be, ha a `--validate` hiányzó fájlt jelez.
Ha minden megvan, felesleges kontextus.

**Vezesd végig a menedzsert lépésenként, visszaigazolást várva.** Ne másold be
az egész listát egyszerre — csak azt a lépést, ami éppen hiányzik.

Minden fájl az `input/` mappába megy, **átnevezés nélkül**. A parser tartalom
alapján ismeri fel őket, nem fájlnév alapján.

## Először rögzítsd a pontos mérési időszakot

A legtöbb HELLO-riport pénzügyi zárás szerint készül, például június 25-től
július 24-ig. Ez teljes értékű havi ciklus: a következő riport július 25-én
induljon, így nincs kimaradó vagy kétszer számolt nap.

Minden napi, Tartalom- és ZoomSphere-exportban ugyanazt a két konkrét dátumot
állítsd be. Ha ettől eltérsz, a hónapok változása nem lesz hiteles. A Meta Ads
export lehet tágabb: a motor nem dobja el és nem arányosítja, hanem a teljes
exportált összeget tájékoztató jelöléssel mutatja.

---

## 1. ZoomSphere — tartalomnaptár

*Ismerős lépés, elég egy emlékeztető.*

ZoomSphere → **Social media Scheduler** → a hónap kijelölése → **Export**.

Fájl: `export_<ügyfél> Social media Scheduler_<dátum>.xlsx`

Ez adja a posztok szövegét, a kreatívokat, a linkeket és a poszt-azonosítókat.
Metrikát nem tartalmaz — az a Metából jön.

## 2. Meta Ads Manager — kampányok

*Ismerős lépés, elég egy emlékeztető.*

Hirdetéskezelő → **Kampányok** → időszak a pontos mérési dátumokra →
**Exportálás** → a szokásos oszlopsablonnal.

A `Jelentés kezdete` és `Jelentés vége` a lekérési ablakot írja le, nem a
kampány tényleges indulását. Kampánykezdést csak külön `Kezdés`, `Indulás` vagy
`Kampány kezdete` oszlopból használunk; ha ilyen nincs, nem találjuk ki.

Fájl: `<ügyfél>-Kampányok-<dátum>.csv`

## 3. Meta Business Suite — Tartalom (Facebook)

Ez adja a poszt-szintű elérést és interakciókat. **Enélkül nincs top-poszt oldal.**

1. Business Suite → **Statisztika**
2. Bal oldali menü → **Tartalom**
3. Fent az időszak a két pontos mérési dátumra
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

**Ezeket nem kell letölteni** — exportban nincsenek, csak a felületről
olvashatók le. A menedzser képernyőképet tesz az `input/` mappába (vagy
bemondja a számot), te pedig a `client.yaml`-be írod:

```yaml
monthly_reach:
  facebook: <szám>
  instagram: <szám>
followers:
  facebook: <szám>
  instagram: <szám>
```

- **Havi elérés:** Business Suite → Eredmények, az időszak a pontos mérési
  dátumokra állítva. A **Facebookon a „Nézők” csempe** az elérés: „Elérés”
  csempe ott nincs, a „Megtekintések” pedig megjelenést mér, nem embert.
  Az Instagramon az **„Elérés”** csempe.
- **Követőszám:** Business Suite → Közönség (az oldal fejléce kerekít, ez
  nem). A következő hónaptól magától számolódik — előző állomány + havi új
  követés —, amíg a hónapok egymás után jönnek, és van követés-csempe. Ha a
  lánc megszakad, a `--validate` újra kéri.

A riportban nincs rájuk kitölthető mező: amit a `--validate` hiányol, azt a
`client.yaml`-ben pótoljuk, nem az ügyfélnek szánt oldalon.

## 8. Előző hónap (opcionális)

Az összehasonlító oldalakhoz. Három út:

- **Egyszerű:** az előző havi `report_data.json` átmásolva `previous.json` néven.
- **Kézzel:** ahol nincs előző havi érték, az összehasonlító oldalon
  szaggatott keretű mező áll. A menedzser beírja, **Mentés**, és a
  `review.json` a hónap mappájába kerül. A kimaradt mezők a következő körben is
  kitölthetők.
- **Első hónapban:** a korábbi riport PDF-jéből javaslat kérhető:

  ```bash
  python tools/import_previous.py "<előző riport.pdf>"
  ```

  Ez **nem ír fájlt** — javaslatot nyomtat. A számok kerekítettek lehetnek
  (`149.3K` → 149 300), és idegen elrendezésnél félrecsúszhatnak, ezért a
  menedzsernek össze kell vetnie a PDF-fel, mielőtt beírja.

## 9. Kampányriporthoz (`report.variant: campaign`)

A kampányriport a **kampány teljes idejére** szól, nem naptári hónapra. Csak az
Ads-export kötelező; a többi kiegészítés.

1. **Ads Manager → Kampányok**, időszak: a kampány első és utolsó napja.
   Nyugodtan exportálhatsz minden kampányt — a riport a `client.yaml`
   `campaign.match` mintája szerint válogat, és a `--validate` kiírja, mit
   választott ki.
2. **Heti görbéhez:** exportálás előtt **Bontás → Idő → Hét**. Ilyenkor egy
   kampány hetente külön sorban jön; a motor összevonja őket, és az idővonalat
   rajzolja belőlük. Az elérést ilyenkor nem adja össze (aki két héten is
   látta, egy ember).
3. **Idővonalhoz:** az oszlopok közé vedd fel a **Kezdés** oszlopot. Nélküle
   nincs „Mikor futott” oldal — kitalált kezdődátumot nem rajzolunk.
4. **Deduplikált elérés, ha több kampány van:** jelöld ki a riport kampányait,
   és az összesítő sor **Elérés** értékét írd a `client.yaml`-be
   (`campaign.reach`). Kampányonként összeadni nem lehet.
5. **Napi csempék (opcionális):** töltsd le őket a kampány idejére **és** az
   előtte lévő, ugyanolyan hosszú időszakra, egyben (pl. egy kéthónapos
   kampánynál négy hónapra). Ebből készül az „alatt vs. előtte” összevetés.

---

## Ha valami nem stimmel

| Hibaüzenet | Mit jelent |
|---|---|
| `hiányzó napi adatok …` | legalább egy nap kimaradt a pontos mérési időszakból; töltsd le újra ugyanazzal a két dátummal |
| `Meta Ads időszak … tájékoztató` | az export használható, de tágabb vagy eltérő ablakot fed; a teljes Ads-összeg bekerül |
| `Más ügyfél adata került a mappába` | két ügyfél fájljai keveredtek |
| `két ZoomSphere export van a mappában` | újraletöltésnél bennmaradt a régi — töröld |
| `ismeretlen napi metrika` | új Meta-csempe; a `client.yaml` `daily_metric_overrides` szakaszába kell felvenni |
| `csonka napi export` | a letöltés félbeszakadt — töltsd le újra |
