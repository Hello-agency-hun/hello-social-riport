"""A design rendszer élő referenciája — generálva, nem kézzel írva.

Kétféle olvasója van, és mindkettőnek mást ad:

- **A pluginnak**, amikor új szekciót tervez: másolható markup-minták, és
  mellettük a szabály, hogy miért úgy. A modell ezt is szövegként olvassa —
  az érték nem a rendereltségben van, hanem abban, hogy a minta *helyes* és
  a szabály ott áll mellette.
- **Embernek**, aki megnyitja: látja a palettát, a tipográfiát és a
  komponenseket úgy, ahogy a riportban megjelennek.

A tokenek és a grafikonok a valódi forrásból jönnek (`templates/brand.css`,
`pipeline/charts.py`), ezért a dokumentum nem tud elcsúszni a rendszertől.
Teszt is őrzi.

Használat:
    python tools/build_styleguide.py
"""

import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import charts  # noqa: E402
from pipeline.assets import FONT_SLOTS, TEMPLATES  # noqa: E402
from pipeline.textio import force_utf8_output  # noqa: E402

TARGET = ROOT / "skills" / "hello-report" / "references" / "design-system.html"

# Mit jelent az adott token, és mennyire szabad használni. Az arányok a
# benchmark riportból mértek — ez tartja vissza a rendszert a harsányságtól.
TOKEN_NOTES = {
    "--ink": ("Elsődleges szöveg", "~50% a kitöltéseknek"),
    "--ink-soft": ("Másodlagos szöveg, feliratok", "~25%"),
    "--rule": ("Keretek, elválasztók, panelhatár", "~10%"),
    "--paper": ("Oldal alapszíne", "háttér"),
    "--paper-alt": ("Panel háttere", "háttér"),
    "--accent": ("Kiemelés, elsődleges grafikon", "~13%"),
    "--brand-rose": ("Grafikon-sorozat, ritka kiemelés", "a hangos színek együtt ~5%"),
    "--brand-sun": ("Ritka kiemelés", "a hangos színek együtt ~5%"),
    "--brand-pink": ("Grafikon-sorozat", "a hangos színek együtt ~5%"),
    "--brand-red": ("Figyelmeztetés, negatív változás", "csak jelzésre"),
    "--brand-blue": ("Grafikon-sorozat", "csak grafikonon"),
}

RULES = [
    (
        "Az oldal 1440 × 810, és a tartalom töltse ki",
        "A <code>.page</code> függőleges flex-doboz. A fő tartalom "
        "(<code>.grid</code>, <code>table</code>, vagy egy <code>.fill</code> "
        "burok) <code>flex: 1</code>-et kap, és középre igazodik. Enélkül minden "
        "a lap tetejére torlódik, és alatta fél oldalnyi üres hely marad — "
        "16:9-es dián ez azonnal feltűnik.",
    ),
    (
        "Szövegblokknak saját flex-doboz kell",
        "Az <code>align-content</code> csak flex/grid konténerre hat. Egy "
        "bekezdés vagy lista körül <code>&lt;div class=\"fill\"&gt;</code> kell, "
        "különben a szöveg a magas terület tetején ragad.",
    ),
    (
        "A listaelem mérete az <code>li</code>-n legyen",
        "A <code>p, li, td, th</code> szabály felülírja az öröklést, tehát a "
        "szülő <code>&lt;ol style=\"font-size:20px\"&gt;</code> nem ér el a "
        "listaelemig. Ez néma: a szöveg egyszerűen kisebb marad.",
    ),
    (
        "Az azonos sorban álló számok osszanak alapvonalat",
        "A <code>.stat</code> fix magasságú és alulra igazít, így a kisebb betűs "
        "<code>.stat--sm</code> (pénznem) felirata nem csúszik följebb a "
        "szomszédjáénál.",
    ),
    (
        "A kreatívot ne vágd",
        "A poszt-képek álló és fekvő arányban is érkeznek. "
        "<code>object-fit: contain</code> fix magassággal — <code>cover</code> "
        "esetén az álló képek közepét vágnánk ki.",
    ),
    (
        "Szín csak tokenből",
        "Sem a sablonokban, sem a <code>charts.py</code>-ban nem lehet beégetett "
        "hex. Minden <code>var(--…)</code>, hogy a paletta egy helyen legyen "
        "állítható. Teszt őrzi.",
    ),
    (
        "Nyomtatásban eltűnik, ami a szerkesztéshez kell",
        "Az üres kézi mezők, a megjegyzés-gombok és a szerkesztő-keretek "
        "<code>@media print</code> alatt rejtettek — az ügyfélhez tiszta "
        "dokumentum megy.",
    ),
    (
        "A narratíva értékei szerkeszthetetlen szigetek",
        "Minden behelyettesített szám <code>&lt;span class=\"val\" "
        "data-ref=\"{…}\"&gt;</code>-be kerül. A körülötte lévő szöveg "
        "átírható, a szám nem — és mentéskor a hivatkozás áll vissza, nem a "
        "kiírt érték.",
    ),
]


def _stylesheet_for_docs() -> str:
    """A riport stíluslapja, de a fontok relatív hivatkozással.

    A riportban a fontok base64-ként ágyazódnak be, hogy a kész HTML önálló
    legyen. Itt viszont ez ~80 KB-tal hizlalná a dokumentumot — és ezt a
    dokumentumot a plugin a kontextusába olvassa be. A repóból megnyitva a
    relatív út ugyanúgy működik.
    """
    css = (TEMPLATES / "brand.css").read_text(encoding="utf-8")
    for slot, filename in FONT_SLOTS.items():
        css = css.replace(slot, f"../../../assets/fonts/{filename}")
    return css + "\n" + (TEMPLATES / "print.css").read_text(encoding="utf-8")


def _tokens() -> list[tuple[str, str]]:
    css = (ROOT / "templates" / "brand.css").read_text(encoding="utf-8")
    root = css[css.index(":root {") : css.index("}", css.index(":root {"))]
    return re.findall(r"(--[a-z-]+):\s*(#[0-9A-Fa-f]{6})", root)


def _example(title: str, markup: str, note: str = "") -> str:
    from html import escape

    return (
        f'<section class="demo"><h3>{escape(title)}</h3>'
        + (f'<p class="note">{note}</p>' if note else "")
        + f'<div class="stage">{markup}</div>'
        + f"<pre><code>{escape(markup.strip())}</code></pre></section>"
    )


def build() -> str:
    from html import escape

    swatches = "".join(
        f'<div class="swatch"><span style="background:{value}"></span>'
        f"<code>{name}</code><b>{value}</b>"
        f"<i>{escape(TOKEN_NOTES.get(name, ('', ''))[0])}</i>"
        f"<u>{escape(TOKEN_NOTES.get(name, ('', ''))[1])}</u></div>"
        for name, value in _tokens()
    )

    rules = "".join(f"<li><b>{title}</b><span>{body}</span></li>" for title, body in RULES)

    series = [
        (date(2026, 7, 1) + timedelta(days=d), v)
        for d, v in enumerate(
            [3, 5, 4, 9, 6, 4, 5, 22, 7, 5, 4, 6, 5, 8, 21, 19, 31, 14, 12, 9,
             11, 8, 7, 6, 9, 12, 10, 8, 9, 7, 5]
        )
    ]

    body = f"""
<header>
  <div class="eyebrow">HELLO Reporting</div>
  <h1>Design rendszer</h1>
  <p class="lead">Ez a dokumentum generált: a tokenek a <code>templates/brand.css</code>-ből,
  a grafikonok a <code>pipeline/charts.py</code>-ból jönnek. Ha a rendszer változik,
  ez is változik — nem tud elcsúszni tőle.</p>
  <p class="note">A kiinduló paletta a HELLO benchmark riportjából mért, nem a brand
  guide teljes palettája: ez a riportálási rendszer, a márka hangos színeinek
  tudatosan visszafogott változata.</p>
</header>

<h2>Színek</h2>
<div class="swatches">{swatches}</div>

<h2>Tipográfia</h2>
<div class="stage type">
  <div class="eyebrow">Szemöldök · eyebrow · 13px/700, ritkított, nagybetűs</div>
  <h2 style="margin:6px 0 14px">Szekciócím · h2 · 46px/900</h2>
  <div class="stat">18 811</div>
  <div class="stat-label">Csempe-felirat · stat-label · 13px/500</div>
  <p style="margin-top:16px;max-width:640px">Kenyérszöveg · 17px/1.5, másodlagos
  színnel. A <strong>kiemelés</strong> elsődleges színt és 700-as vastagságot kap.</p>
  <p class="note">Lábjegyzet · note · 13px</p>
</div>

<h2>Az oldal felépítése</h2>
<ol class="rules">{rules}</ol>

<h2>Komponensek</h2>
{_example(
    "Statisztika-csempe",
    '<div class="grid" style="grid-template-columns:repeat(3,1fr)">'
    '<div><div class="stat">18 811</div><div class="stat-label">poszt-elérés</div></div>'
    '<div><div class="stat stat--sm">472,71 EUR</div>'
    '<div class="stat-label">hirdetési költés</div></div>'
    '<div><div class="stat accent">33,2×</div>'
    '<div class="stat-label">a boost szorzója</div></div></div>',
    "Pénznemnél <code>stat--sm</code>, különben két sorba törne. A fix "
    "magasság miatt a feliratok akkor is egy vonalban maradnak.",
)}
{_example(
    "Panel",
    '<div class="panel"><h3 class="accent" style="margin-bottom:10px">Mi működött</h3>'
    '<p>Panelbe kerül minden, ami önálló egységet alkot: kártya, csempecsoport, '
    'kiemelt blokk.</p></div>',
)}
{_example(
    "Változásjelző",
    '<div class="grid" style="grid-template-columns:repeat(3,1fr)">'
    '<div class="panel"><div class="stat">'
    '<span class="delta delta--up">↑</span> 1 525</div>'
    '<div class="stat-label">Felkeresések</div>'
    '<p class="note" style="margin-top:8px">előző hónap: 1 113 · +412 (37,0%)</p></div>'
    '<div class="panel"><div class="stat">'
    '<span class="delta delta--down">↓</span> 255</div>'
    '<div class="stat-label">Interakciók</div>'
    '<p class="note" style="margin-top:8px">előző hónap: 342 · −87 (−25,4%)</p></div>'
    '<div class="panel"><div class="stat">'
    '<span class="delta delta--flat">·</span> 634</div>'
    '<div class="stat-label">Felkeresések</div>'
    '<p class="note" style="margin-top:8px">nincs előző havi adat</p></div></div>',
    "Minden kiszámolt változás mellett ott a nyíl. Az irányt a <b>nyíl</b> "
    "mutatja, nem a szín — ezért mindkét irány ugyanaz a pink. Egy csökkenést "
    "pirosra festeni ítélet volna, márpedig nem minden visszaesés rossz hír: a "
    "hirdetési költés csökkenése például nem az. A riport a számot mutatja meg, "
    "az értékelés a szövegben van. A halvány <code>·</code> nem nulla változás, "
    "hanem adathiány. A mínusz valódi mínuszjel (−), nem kötőjel: a kötőjel a "
    "számjegyek mellett elvész.",
)}
{_example(
    "Kézi adatmező",
    '<div class="grid" style="grid-template-columns:1fr 1fr">'
    '<div class="manual-slot" data-manual="reach_facebook">'
    '<div class="manual-input" data-placeholder="—"></div>'
    '<div class="stat-label">Facebook havi elérés</div>'
    '<p class="note" style="margin-top:6px">Business Suite → Elérés csempe</p></div>'
    '<div class="panel"><div class="stat">92 400</div>'
    '<div class="stat-label">Facebook havi elérés '
    '<span class="manual-mark">kézi adat</span></div></div></div>',
    "Ami hiányzik, de beszerezhető, az látható és kitölthető marad, és kiírja, "
    "honnan szerezhető be. Üresen nyomtatásban nem jelenik meg.",
)}
{_example(
    "Narratíva-blokk szerkeszthető értékkel",
    '<p data-narrative="executive_summary" style="font-size:20px">'
    'A boost <span class="val" data-ref="{{cross.reach_multiplier|x}}">33,2×</span> '
    'elérést hozott az organikus átlaghoz képest.</p>',
    "A <code>.val</code> sziget nem szerkeszthető, és a hivatkozását "
    "<code>data-ref</code>-ben hordozza — mentéskor az áll vissza.",
)}

<h2>Grafikonok</h2>
<p class="note">Mind inline SVG, tokenből színezve. Külső chart-könyvtár nincs;
a nyomtatás így vektoros marad.</p>
{_example(
    "Napi trendvonal",
    f'<div class="panel" style="max-width:640px">{charts.line_chart(series, label="Példa", height=200)}</div>',
    "Rácsvonalak értékkel, a három legerősebb nap megjelölve dátummal, a lábban "
    "az időszak összege. A csúcsok között legalább öt nap, különben a címkék "
    "egymásra csúsznának.",
)}
{_example(
    "Vízszintes oszlop",
    f'<div class="panel" style="max-width:640px">{charts.bar_chart([("Séfünk ajánlata", 9046), ("Gambas Pil-Pil", 4142), ("Frissen, roppanósan", 2068)], label="Példa")}</div>',
    "Rangsorhoz. A felirat a sáv fölött, az érték a végén.",
)}
{_example(
    "Gyűrű",
    f'<div class="panel" style="max-width:340px">{charts.donut([("Boostolt", 17246), ("Organikus", 1565)], label="Példa")}</div>',
    "Kétosztatú megoszláshoz. A jelmagyarázat magyar tizedesvesszőt használ, "
    "mint a riport szövege.",
)}
"""

    return (
        "<!doctype html>\n<html lang=\"hu\"><head><meta charset=\"utf-8\">"
        "<title>HELLO Reporting — design rendszer</title>"
        f"<style>{_stylesheet_for_docs()}</style>"
        "<style>"
        "body{background:var(--paper);padding:56px;max-width:1100px;margin:0 auto}"
        "header{margin-bottom:48px}"
        "h1{font-size:60px;margin:8px 0 18px}"
        "h2{font-size:30px;margin:56px 0 18px;padding-top:20px;"
        "border-top:1px solid var(--rule)}"
        "h3{font-size:16px;margin-bottom:8px}"
        ".lead{font-size:19px;max-width:760px;color:var(--ink)}"
        ".swatches{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}"
        ".swatch{display:grid;grid-template-columns:44px 132px 90px 1fr;"
        "gap:12px;align-items:center;border:1px solid var(--rule);"
        "border-radius:10px;padding:10px 14px}"
        ".swatch span{width:44px;height:32px;border-radius:6px;"
        "border:1px solid var(--rule)}"
        ".swatch b{font-size:13px}.swatch i{font-size:13px;font-style:normal;"
        "color:var(--ink-soft)}"
        ".swatch u{grid-column:2/5;text-decoration:none;font-size:12px;"
        "color:var(--ink-soft)}"
        ".rules{padding-left:20px}"
        ".rules li{margin-bottom:14px}.rules b{display:block;color:var(--ink)}"
        ".rules span{font-size:15px}"
        ".demo{margin:22px 0 34px}"
        ".stage{border:1px solid var(--rule);border-radius:12px;padding:24px;"
        "background:var(--paper-alt);margin-bottom:10px}"
        "pre{background:var(--ink);color:var(--paper);border-radius:10px;"
        "padding:14px 16px;overflow-x:auto;font-size:12px;line-height:1.55}"
        "code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}"
        "</style></head><body>" + body + "</body></html>"
    )


if __name__ == "__main__":
    force_utf8_output()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    html = build()
    TARGET.write_text(html, encoding="utf-8")
    print(f"{TARGET.relative_to(ROOT)}  {len(html):,} byte".replace(",", " "))
