# Hogyan írjuk a riport szövegét

Ez a dokumentum a **riport hangneméről** szól — arról, amit az ügyfél olvas.
A menedzserrel folytatott beszélgetés ettől külön él, és lehet könnyed; ez itt
nem az.

## Hangnem

**Komoly, szakmai, ügyfélnek kiküldhető.** Egy ügynökség ír a megbízójának
arról, mi történt a pénzével és a márkájával.

- Konkrét, nem általános. „A séf-ajánlat vitte a legtöbb elérést" — nem
  „a tartalmaink jól teljesítettek".
- Állítást tesz, nem felsorol. A vezetői összefoglaló első mondata legyen a
  legfontosabb megállapítás.
- Nem lelkendezik. A „fantasztikus", „kiemelkedő", „szuper" szavak semmit nem
  mondanak; a szám mondja meg, jó-e.
- Nem mentegetőzik. Ha valamit nem mértünk, arról a riportban nem írunk.

## A szabály: számot nem lehet leírni

A narratíva szövegében **minden számjegy tiltott**. Számra csak hivatkozni lehet:

```json
"executive_summary":
  "Organikusan egy poszt átlagosan {cross.avg_reach_organic_post} embert ért el,
   boosttal {cross.avg_reach_boosted_post}-t — {cross.reach_multiplier|x} a
   különbség, {cross.boost_spend|money} összes költésből."
```

A build elutasítja a leírt számot, és megmondja, melyiket.

**Ez magyarul nem kényelmetlen.** „A hat legjobb poszt", „a harmadik hete futó
kampány" — a számnevek kiírva természetesebbek is. Ahol tényleg szám kell, ott
adat van mögötte, tehát van mire hivatkozni.

Ha nincs mező arra, amit mondani szeretnél: **akkor azt nem tudjuk**, és nem is
állítjuk. Ez nem korlát, hanem a riport hitelessége.

### Formázók

| Írás | Eredmény |
|---|---|
| `{cross.avg_reach_organic_post}` | `130` |
| `{paid.spend\|money}` | `472,71 EUR` |
| `{cross.boosted_share_of_post_reach\|pct}` | `91,7%` |
| `{cross.reach_multiplier\|x}` | `33,2×` |
| `{meta.period\|month}` | `2026. július` |
| `{meta.client\|raw}` | `Larus Étterem` |

A mezők a `report_data.json`-ból jönnek; a teljes szerkezetet ott látod.

## Az öt blokk

**`executive_summary`** — három-négy mondat arról, mi történt és miért. A
legfontosabb állítással kezdj.

**`key_finding`** — egyetlen megállapítás, ami befolyásolja a következő havi
döntést. `title`: rövid állítás. `body`: két-három mondat indoklás.

**`what_worked`** — két-három pont, mindegyik konkrét tartalomra vagy kampányra
mutat. Ne „a videós tartalom", hanem melyik.

**`what_to_improve`** — két-három pont. Ne hibáztass, és ne az adathiányról írj:
azt írd le, mit csinálunk másképp.

**`next_steps`** — három-négy lépés, fontossági sorrendben, mindegyik cselekvés.
Az első legyen a legfontosabb, ne a legkönnyebb.

## Jó és rossz példa ugyanarra

❌ **Rossz**

> A hónap során összesen 29 tartalmat tettünk közzé, amelyek szuper eredményeket
> hoztak. A boostolt posztok kiemelkedően teljesítettek, bár sajnos az Instagram
> poszt-szintű adatai nem álltak rendelkezésünkre.

Három baj: leírt szám (`29`), tartalmatlan minősítés („szuper", „kiemelkedően"),
és mentegetőzés olyasmiért, ami az ügyfelet nem érdekli.

✅ **Jó**

> Egy organikus poszt átlagosan {cross.avg_reach_organic_post} embert ért el,
> boosttal {cross.avg_reach_boosted_post}-t — {cross.reach_multiplier|x} a
> különbség, poszonként néhány eurós költésből. A hónap elérésének nagy része
> tehát nem a tartalomtól, hanem a támogatástól függött.

Ugyanaz az adat, de állítást tesz, és eljut oda, ami a döntést befolyásolja.

## Amit kerülj

- **Tartalmatlan minősítés:** „remekül teljesített", „jelentős növekedés",
  „stabil eredmények". Ezek mindenre ráhúzhatók, tehát semmit nem mondanak.
- **Passzív szerkezet:** „a kampány elindításra került". Mi indítottuk el.
- **Adathiány emlegetése:** „az Instagram-adatok korlátozottan álltak
  rendelkezésre". Az ügyfél ebből azt olvassa ki, hogy nem értünk a munkánkhoz.
  A hiánylista a menedzsernek szól, a `--validate` kimenetében.
- **Állítás mező nélkül:** ha nincs adat rá a `report_data.json`-ben, akkor azt
  nem tudjuk. Ne írd le.
- **Túl hosszú blokkok.** A riport nézhető, nem olvasandó. Egy oldal egy gondolat.

## A `performance` blokk — itt vannak a kész felismerések

A riportadat `performance.<csatorna>` szakasza nem nyers szám, hanem **már
megtalált összefüggés**. Ha valamelyik igaz, azt írd is meg — ezekért olvas az
ügyfél riportot.

| mező | mit jelent | mikor érdemes írni róla |
|---|---|---|
| `top_is_reach_leader` | ugyanaz-e a legnagyobb elérésű és a legjobban teljesítő poszt | ha **hamis**, az önmagában megállapítás |
| `top` | a legjobban teljesítő poszt | mindig |
| `reach_leader` | a legnagyobb elérésű | ha eltér a `top`-tól |
| `best_unboosted` | a támogatás nélküli mezőny legjobbja | ha `best_unboosted_beats_typical` igaz |
| `median_engagement_rate` | a csatorna szokásos szintje | viszonyítási alapnak |

### A legfontosabb minta

Ha a **`top_is_reach_leader` hamis**, akkor a legnagyobb elérésű poszt nem a
legjobb poszt. Ez majdnem mindig ugyanazt jelenti: **a költés vitte az elérést,
a tartalom pedig máshol működött.** Ez erős, cselekvésre váltható megállapítás,
mert megmondja, mit kellene legközelebb megtámogatni.

Példa arra, hogyan lehet ezt leírni szám kiírása nélkül:

> A hónap legnagyobb elérésű bejegyzése a nézők
> {performance.facebook.reach_leader.engagement_rate|pct}-át mozdította meg; a
> Gambas Pil-Pil ételfotója ugyanennek a többszörösét,
> {performance.facebook.top.engagement_rate|pct}-ot. Az elérést tehát a
> támogatás adta, a rezonanciát a kreatív — és a kettő nem ugyanaz a poszt volt.

### A másik minta

Ha `best_unboosted_beats_typical` igaz, van egy poszt, ami **támogatás nélkül
ment nagyot magához képest**. Ez a következő hónap legjobb boost-jelöltje, és
érdemes név szerint kiemelni. A kis elérés itt nem gyengeség: azt jelenti, hogy
kevés emberhez jutott el, de akikhez igen, azok reagáltak.

### Amit ne csinálj

**Ne nevezd „legnépszerűbbnek" a legnagyobb elérésű posztot.** Az elérést a
költés dönti el; a népszerűséget a rezonancia.

### Szóhasználat

Két szót következetesen használunk, mert a Meta felülete is így hívja őket, és
a menedzser is ezen a nyelven beszél az ügyféllel:

| ezt írd | ezt ne |
|---|---|
| **nézők** (akikhez eljutott a poszt) | „látók" |
| **organikus** (támogatás nélküli) | „szerves" |

## Amire érdemes figyelni ennél az adatnál

- Az **„oldal összes" nem organikus** — a fizetett aktivitás eredménye is benne
  van. Ha erről írsz, ne nevezd organikusnak.
- Az **eredménytípusok nem összeadhatók** (`Elérés` és `Poszt-interakció` mást
  mér). A riport ezért mutatja őket külön sorokban; a szövegben se vond össze őket.
- A **poszt-elérések összege nem havi elérés.** Aki több posztot is látott, abban
  többször szerepel. Arányra jó, összegként félrevezető.
