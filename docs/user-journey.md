# A menedzser útja — végigjárva

Egy kitalált ügyfélen (**PETI Pörkölőműhely**) végigmentem a teljes folyamaton
úgy, mintha először látnám. A cél nem az volt, hogy működjön, hanem hogy
kiderüljön, **hol akad el az, aki nem ismeri a rendszert.**

A készlet: 12 Facebook- és 10 Instagram-poszt, 3 always-on és 7 boostolt
kampány, nyolc napi csempe, hat story. Szándékosan volt benne egy poszt, amiről
a ZoomSphere nem tud, és a legnagyobb elérésű poszt szándékosan nem a legjobban
teljesítő.

---

## Az út, ahogy ténylegesen lezajlott

| # | Lépés | Eredmény |
|---|---|---|
| 1 | `--validate` üres mappán | ✅ kitöltött `client.yaml`-sablont adott, 4-ből 3 mezővel |
| 2 | `client.yaml` kitöltve | ❌ **ZoomSphere-dátum → nyers stack trace** |
| 3 | újra | ❌ `Megtekintések` csempe csatornája |
| 4 | újra | ⚠️ minden IG-poszt kreatív nélkül |
| 5 | újra | ✅ átment, de hiányzott a havi elérés |
| 6 | `monthly_reach` beírva | ✅ tiszta futás |
| 7 | narratíva megírva, build | ✅ 23 oldal, 0 túlcsordulás |
| 8 | `review.json` visszaküldve | ✅ 2 szövegjavítás + 8 kézi adat + 1 megjegyzés |
| 9 | `--apply-review` | ✅ hivatkozások sértetlenek, változás-oldalak feltöltve |

**Négy körben jutottam el az első sikeres futásig.** Ez a legfontosabb tanulság.

---

## Amit rosszul csináltunk

### 1. Négy hibaüzenet egymás után, mindegyik külön kör

Minden `--validate` **az első hibánál megáll**. A menedzser kijavít egyet,
újrafuttat, kap egy másikat. Négyszer.

Pedig a négyből három **egyszerre látható lett volna**: a hiányzó
`client.yaml`, a csatorna nélküli csempe és a hiányzó havi elérés egymástól
független. Csak a stack trace volt olyan, ami tényleg megállítja a feldolgozást.

> **Javítva:** a `--validate` most összegyűjti, amit egy körben lehet, és
> **számozott listában** adja vissza. Négy körből egy lett.

### 2. A ZoomSphere-dátum nyers `ValueError`-t dobott

`_strptime` stack trace, tizenkét sor, a fájl neve sehol. Ebből a menedzser nem
tudhatja, hogy a fájllal van baj, nem a programmal.

A leggyakoribb ok prózai: **valaki megnyitotta Excelben és mentette**, az pedig
átírja a dátumformátumot.

> **Javítva:** megnevezi a fájlt, a várt formátumot és a valószínű okot.

### 3. Az Instagram-poszt némán elvesztette a kreatívját

A join **poszt-azonosító alapján** párosít. Ha a ZoomSphere és a Meta nem
ugyanazt az azonosítót tárolja — Instagramnál ez reális —, a poszt kreatív
nélkül marad, és erről **semmi nem szólt**. A Larus-készletben ez sosem derült
volna ki, mert ott nem volt IG Tartalom export.

> **Javítva:** ha az azonosító nem talál, a rendszer **szöveg szerint** próbálja
> meg. Gyengébb bizonyíték, de sokkal jobb egy üres képnél. A `--validate`
> pedig név szerint felsorolja, ami így is kimaradt.

### 4. A `--validate` kimenete nyers markdownt tartalmazott

`**Nézők**` — csillagokkal, terminálon. És a „miért nem számolható"
magyarázat **csatornánként megismételve**, ráadásul egy *másik ügyfél* júliusi
számaival.

> **Javítva:** idézőjel a félkövér helyett, a magyarázat egyszer szerepel, és
> általánosan fogalmaz.

---

## Amit jól csináltunk

**A bootstrap kitöltötte a `client.yaml` négy mezőjéből hármat.** Az
oldalazonosítót és az oldalnevet kiolvasta a Tartalom exportból. Csak az
Instagram-felhasználónevet és a követőszámot kellett beírni — azok tényleg nem
szerepelnek sehol.

**A kreatív nélküli posztok figyelmeztetése azonnal megtérült.** Ez a
figyelmeztetés egy nappal korábban készült, és rögtön elkapta a 3. pontban
leírt hibát. Enélkül csak a kész riportban láttam volna meg — és ott a
**legjobban teljesítő poszt** helyén állt a helyőrző.

**A teljesítmény-rangsor működik idegen adaton is.** Mindkét csatornán ugyanazt
találta: a legnagyobb elérésű bejegyzés a leggyengébben teljesítő. Facebookon a
látók 0,9%-a reagált a legtöbbet elérő posztra, míg a támogatás nélküli
kóstoló-meghívóra 22,1%. Ez a megállapítás vitte az egész narratívát.

**A review-kör sértetlenül visszahozta a hivatkozásokat.** Átírtam egy címet és
egy listaelemet a `{performance.facebook.top.vs_typical|x}` hivatkozással
együtt — a `--apply-review` a hivatkozást megőrizte, nem a behelyettesített
számot írta vissza.

**A kézi adatbevitel feltöltötte a változás-oldalakat.** Nyolc előző havi
értékből mind a három nyílállapot előjött: növekedés, csökkenés és stagnálás.

---

## Amit érdemes tudni, de nem hiba

**23 oldal lett 22 helyett.** Mert mindkét csatornáról volt Tartalom export,
tehát mindkettő megkapta a teljes szekciót. Ez helyes viselkedés; a
korlát ügyfélenként változik.

**A `content.stories_by_channel` üres maradt.** A story-sorok a ZoomSphere-ben
nem hordoztak csatorna-információt. A riportot nem rontotta el, de ha egy
ügyfélnél sok a story, érdemes ránézni.

---

## A folyamat, ahogy most kinéz

```
1. „Csinálj riportot a PETI-nek júliusra"
     → megkérdezi az ügyfelet és a hónapot, létrehozza a mappát, és VÁR

2. Feltöltöd az exportokat az input/ mappába

3. --validate
     → EGY listában megmondja, mi hiányzik és mit kell beírni

4. Kitöltöd a client.yaml-t (követőszám, havi elérés)

5. --validate
     → tiszta futás

6. Megírja a narratívát, megépíti a riportot

7. Böngészőben átírod, ami nem tetszik, „Mentés a mappába"

8. Szólsz, hogy mentettél → --apply-review → kész
```

**Öt lépés, amiből kettő a tiéd.**
