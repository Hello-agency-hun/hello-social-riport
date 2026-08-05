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

## Amire érdemes figyelni ennél az adatnál

- Az **„oldal összes" nem organikus** — a fizetett aktivitás eredménye is benne
  van. Ha erről írsz, ne nevezd organikusnak.
- Az **eredménytípusok nem összeadhatók** (`Elérés` és `Poszt-interakció` mást
  mér). A riport ezért mutatja őket külön sorokban; a szövegben se vond össze őket.
- A **poszt-elérések összege nem havi elérés.** Aki több posztot is látott, abban
  többször szerepel. Arányra jó, összegként félrevezető.
