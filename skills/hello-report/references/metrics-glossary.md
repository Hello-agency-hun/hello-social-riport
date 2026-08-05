# Metrika-szótár

A riportban szereplő mérőszámok jelentése, és amit a leggyakrabban félreértenek.

## Alapfogalmak

**Elérés** — hány **egyedi ember** látta a tartalmat legalább egyszer. Aki
háromszor látta, egynek számít.

**Megjelenés** — hányszor jelent meg a tartalom, ismétlődéssel együtt. Ha a
megjelenés nő, de az elérés nem, akkor ugyanaz a közönség látja többször.

**Felkeresés** — hányan nyitották meg az oldalt vagy a profilt.

**Interakció** — reakció, hozzászólás, megosztás, mentés. A megosztás és a
mentés a legerősebb jelzés: az egyik továbbadja, a másik visszatér rá.

**Hivatkozáskattintás** — hányan kattintottak ki a weboldalra.

**Gyakoriság** — megjelenés ÷ elérés. Hányszor látta a tartalmat egy átlagos
ember. Ha nő, miközben az átkattintás nem, az a kreatív kifáradásának első jele.

---

## Négy dolog, amit könnyű elrontani

### 1. A napi elérés nem adható össze havi eléréssé

Az elérés **egyedi emberek száma**. Aki 4-én és 20-án is látott minket, az egy
ember — de két napi számban is szerepel. Harmincegy napi elérés összege tipikusan
kétszerese-négyszerese a valós havi elérésnek.

A helyes havi érték csak a Meta felületéről olvasható le, havi időszakra
állítva. A pipeline ezért **kódszinten tiltja** az elérés összegzését.

### 2. Az „oldal összes" nem organikus

A Business Suite napi csempéi (felkeresések, interakciók, kattintások) a
**fizetett aktivitás eredményét is tartalmazzák.**

A Larus júliusi adatában ez látványos: a havi 1 227 Facebook-kattintásból 830
négy nap alatt keletkezett — pontosan akkor, amikor két always-on kampány futott.
Ez nem szezonalitás, hanem a hirdetés.

A riport ezért „oldal összes"-ként címkézi, nem organikusként.

### 3. Az eredménytípusok nem összeadhatók

A Meta Ads exportjában az `Eredmények` oszlop **kampányonként mást jelent** —
az `Eredmény jelzése` oszlop mondja meg, mit:

| Eredmény jelzése | Mit számol |
|---|---|
| `reach` | egyedi elérés |
| `actions:omni_landing_page_view` | érkezésioldal-megtekintés |
| `profile_visit_view` | profil-felkeresés |
| `actions:post_engagement` | poszt-interakció |
| `actions:link_click` | hivatkozáskattintás |
| `actions:click_to_call_native_call_placed` | telefonhívás |

Egy 123 568-as elérés-eredményt és egy 428-as poszt-interakciót összeadni
értelmetlen. A riport ezért mutatja őket külön sorokban.

### 4. A poszt-elérések összege nem havi elérés

A riport „poszt-elérés" néven közli a hónap posztjainak elérés-összegét. Ez
**arányszámításra jó** (mennyivel ér el többet egy boostolt poszt), de nem havi
elérés — aki több posztot is látott, többször szerepel benne.

---

## Organikus és fizetett

A poszt-szintű elérés a Meta Tartalom exportjából jön, és **teljes elérés**: a
fizetett is benne van. A hirdetési oldalról külön tudjuk, mennyi elérést hozott
a kampány.

A riport ezért két **mért** számot mutat egymás mellett:

```
Elérés               9 046
ebből fizetett       8 398        15,95 EUR
```

Organikus elérést **nem** számolunk kivonással. A két halmaz átfed — aki a
hirdetést is és a hírfolyamban is látta, mindkettőben szerepel —, így a
különbség nem tiszta organikus érték.

## Mit nem mérünk

- **Story-teljesítmény.** A Tartalom export csak feed-posztokat tartalmaz. A
  story-k darabszámmal és kreatívval jelennek meg.
- **Instagram poszt-szintű organikus adat**, amíg nincs IG Tartalom export.
  Ilyenkor az Instagram-posztokról a kreatívot, a szöveget és a fizetett
  hátteret tudjuk — az organikus elérés nem nulla, hanem **ismeretlen**, és
  ezért nem is szerepel az átlagokban.
