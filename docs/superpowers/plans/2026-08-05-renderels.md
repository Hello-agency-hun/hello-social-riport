# HELLO Reporting — 2. terv: Renderelés

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A lezárt `report_data.json`-ból önálló, brandelt, 16:9-es HTML riport, böngészőből PDF-be nyomtatható — külső hálózati függőség nélkül megnyitva is.

**Architecture:** A renderelő réteg **kizárólag a `report_data.json`-t olvassa**, forrásfájlt soha. A design tokenek egy helyen élnek (`templates/brand.css`), a grafikonok ezekből színeződnek. A `charts.py` közvetlenül SVG-t generál — nincs matplotlib, nincs JS chart-könyvtár. A képek és a fontok base64-ként beágyazódnak, így a kész HTML egyetlen, offline is működő fájl.

**Tech Stack:** Python 3.12, Jinja2, Pillow (képméretezés), requests (letöltés), fonttools+brotli (csak a fontok egyszeri vendorálásához, fejlesztői függőség).

**Előfeltétel:** az 1. terv kész (`pipeline/build.py`, `pipeline/cli.py`, 83 teszt zöld). A `tests/fixtures/larus-2026-07/report_data.golden.json` a renderelés bemenete.

---

## Kiinduló mérések

Ezek nem tervezői döntések, hanem a benchmark riportból (`HELLO_CLIENT'S Google Ads Report.pdf`) kinyert tények. A rajzoló-utasításokban előforduló kitöltések gyakorisága:

```
#0A0A0A   318×   szöveg
#6B665D   172×   másodlagos szöveg
#4CD892   130×   akcentus (Aquamarine)
#E4E0D8    72×   keretek, panelek
#FFFFFF/#FAFAFA/#FFFDF9   alapszínek
#FF33CC    20×  ┐
#FFFA8E    14×  ├ hangos márkaszínek, együtt ~5%
#FF91E7    12×  ┘
```

Font: **Open Sauce One** (Regular / Medium / Bold / Black). Oldalméret: **1440 × 810**.

---

## Fájlstruktúra

| Fájl | Felelősség |
|---|---|
| `tools/vendor_fonts.py` | egyszeri: TTF letöltés → woff2, a repóba |
| `assets/fonts/*.woff2` | commitolt fontfájlok + OFL licenc |
| `templates/brand.css` | design tokenek és tipográfia — az egyetlen hely, ahol szín van |
| `templates/print.css` | oldaltörés, 16:9 nyomtatás |
| `pipeline/charts.py` | SVG grafikonok, tokenekből színezve |
| `pipeline/images.py` | képletöltés, méretezés, base64, cache, placeholder |
| `pipeline/assets.py` | font- és CSS-beágyazás |
| `pipeline/render.py` | Jinja2 környezet, a riport összeállítása |
| `templates/report.html.j2` | az oldalak váza, egyetlen sablonban |

Elv: a `charts.py` és az `images.py` semmit nem tud a riport szerkezetéről, a `render.py` semmit nem tud a képletöltésről. Mindegyik önállóan tesztelhető.

---

## Task 1: Fontok vendorálása

**Files:**
- Create: `tools/vendor_fonts.py`
- Create: `assets/fonts/` (4 woff2 + licenc)
- Modify: `pyproject.toml`
- Test: `tests/test_assets.py`

- [ ] **Step 1: Vedd fel a fejlesztői függőséget**

`pyproject.toml`, az `[project.optional-dependencies]` szakaszban:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "fonttools[woff]>=4.50"]
```

A `fonttools` **csak a fontok egyszeri konvertálásához kell**. A kész woff2 fájlok
a repóba kerülnek, így a menedzsernek soha nem kell telepítenie.

- [ ] **Step 2: Írd meg a vendoráló scriptet**

`tools/vendor_fonts.py`:

```python
"""Open Sauce One vendorálása a repóba. Egyszer fut, az eredménye commitolva.

A font OFL licencű, tehát terjeszthető. A HELLO brand guide `Open Sauce Sans`-t
nevez meg, a benchmark riport viszont `Open Sauce One`-t használ — a riportban
az utóbbi az irányadó.
"""

import io
import sys
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/marcologous/Open-Sauce-Fonts/master"
WEIGHTS = ["Regular", "Medium", "Bold", "Black"]
TARGET = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "hello-reporting"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    from fontTools.ttLib import TTFont

    TARGET.mkdir(parents=True, exist_ok=True)

    licence = _download(f"{RAW}/Open%20Sauce%20One%20OFL.txt")
    (TARGET / "OFL.txt").write_bytes(licence)
    print(f"OFL.txt  {len(licence)} byte")

    for weight in WEIGHTS:
        raw = _download(f"{RAW}/fonts/ttf/OpenSauceOne-{weight}.ttf")
        font = TTFont(io.BytesIO(raw))
        font.flavor = "woff2"
        out = TARGET / f"OpenSauceOne-{weight}.woff2"
        font.save(out)
        print(f"{out.name}  {len(raw)} byte ttf → {out.stat().st_size} byte woff2")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Futtasd**

Run: `pip install -e ".[dev]"` majd `python tools/vendor_fonts.py`

Expected: öt fájl az `assets/fonts/` alatt, a woff2-k érzékelhetően kisebbek a TTF-nél
(tipikusan 25-35%-a). Ha a letöltés hálózati hiba miatt elbukik, **ne írj helyette
placeholder fájlt** — jelezd, és álljon meg a task.

- [ ] **Step 4: Írd meg a tesztet**

`tests/test_assets.py`:

```python
from pathlib import Path

import pytest

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
WEIGHTS = ["Regular", "Medium", "Bold", "Black"]


@pytest.mark.parametrize("weight", WEIGHTS)
def test_font_is_vendored(weight):
    path = FONTS / f"OpenSauceOne-{weight}.woff2"
    assert path.exists(), f"{path.name} hiányzik — futtasd: python tools/vendor_fonts.py"
    assert path.read_bytes()[:4] == b"wOF2", "nem woff2 fájl"


def test_licence_is_shipped():
    """OFL: a licencszöveget együtt kell terjeszteni a fonttal."""
    assert (FONTS / "OFL.txt").exists()
```

- [ ] **Step 5: Futtasd**

Run: `pytest tests/test_assets.py -q`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tools/vendor_fonts.py assets/fonts tests/test_assets.py
git commit -m "feat: Open Sauce One vendoralasa woff2-kent"
```

---

## Task 2: Design tokenek

**Files:**
- Create: `templates/brand.css`
- Test: `tests/test_brand.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_brand.py`:

```python
import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parent.parent / "templates" / "brand.css"

# A benchmark riportból mért paletta. Ha ez elmozdul, a riport eltér a HELLO
# vizuális rendszerétől — ezért van tesztbe kötve, nem csak dokumentálva.
TOKENS = {
    "--ink": "#0A0A0A",
    "--ink-soft": "#6B665D",
    "--rule": "#E4E0D8",
    "--paper": "#FFFDF9",
    "--paper-alt": "#FAFAFA",
    "--accent": "#4CD892",
    "--brand-rose": "#FF33CC",
    "--brand-sun": "#FFFA8E",
    "--brand-pink": "#FF91E7",
    "--brand-red": "#FF321D",
    "--brand-blue": "#025CC6",
}


@pytest.mark.parametrize("token, value", TOKENS.items())
def test_token_has_the_measured_value(token, value):
    text = CSS.read_text(encoding="utf-8")
    match = re.search(rf"{re.escape(token)}\s*:\s*(#[0-9A-Fa-f]{{6}})", text)
    assert match, f"{token} nincs definiálva a brand.css-ben"
    assert match.group(1).upper() == value


def test_page_is_16_by_9():
    text = CSS.read_text(encoding="utf-8")
    assert "--page-w: 1440px" in text
    assert "--page-h: 810px" in text


def test_fonts_are_embedded_by_placeholder_not_by_url():
    """A kész HTML offline is működik — külső fonthivatkozás nem maradhat benne."""
    text = CSS.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in text
    assert "http://" not in text and "https://" not in text
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_brand.py -q`
Expected: FAIL — `FileNotFoundError` a `templates/brand.css`-re.

- [ ] **Step 3: Írd meg a `templates/brand.css`-t**

```css
/* HELLO Reporting — design tokenek.
 *
 * Forrás: a HELLO_CLIENT'S Google Ads Report benchmark PDF rajzoló-utasításaiból
 * mért paletta. Ez a riportálási rendszer: a brand guide hangos palettájának
 * tudatosan visszafogott változata.
 *
 * Használati arány a benchmarkban — ettől ne térj el:
 *   semleges tónusok  ~80%
 *   --accent          ~13%
 *   hangos márkaszínek ~5%, csak kiemelésre
 *
 * Szín kizárólag itt szerepelhet. A sablonok és a charts.py var(--…)-t használ.
 */

@font-face { font-family: "Open Sauce One"; font-weight: 400; font-style: normal;
             src: url("__FONT_REGULAR__") format("woff2"); font-display: block; }
@font-face { font-family: "Open Sauce One"; font-weight: 500; font-style: normal;
             src: url("__FONT_MEDIUM__") format("woff2"); font-display: block; }
@font-face { font-family: "Open Sauce One"; font-weight: 700; font-style: normal;
             src: url("__FONT_BOLD__") format("woff2"); font-display: block; }
@font-face { font-family: "Open Sauce One"; font-weight: 900; font-style: normal;
             src: url("__FONT_BLACK__") format("woff2"); font-display: block; }

:root {
  --ink: #0A0A0A;
  --ink-soft: #6B665D;
  --rule: #E4E0D8;
  --paper: #FFFDF9;
  --paper-alt: #FAFAFA;
  --accent: #4CD892;

  --brand-rose: #FF33CC;
  --brand-sun: #FFFA8E;
  --brand-pink: #FF91E7;
  --brand-red: #FF321D;
  --brand-blue: #025CC6;

  --page-w: 1440px;
  --page-h: 810px;
  --pad: 72px;

  --font: "Open Sauce One", "Helvetica Neue", Helvetica, Arial, sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font);
  color: var(--ink);
  background: var(--rule);
  -webkit-font-smoothing: antialiased;
}

.page {
  width: var(--page-w);
  height: var(--page-h);
  padding: var(--pad);
  background: var(--paper);
  margin: 24px auto;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.eyebrow {
  font-size: 13px; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink-soft);
}
h1 { font-size: 84px; font-weight: 900; line-height: .98; letter-spacing: -.02em; }
h2 { font-size: 46px; font-weight: 900; line-height: 1.05; letter-spacing: -.015em; }
h3 { font-size: 22px; font-weight: 700; }
p, li, td, th { font-size: 17px; line-height: 1.5; color: var(--ink-soft); }
strong { color: var(--ink); font-weight: 700; }

.stat { font-size: 64px; font-weight: 900; line-height: 1; letter-spacing: -.02em; }
.stat-label { font-size: 13px; font-weight: 500; letter-spacing: .1em;
              text-transform: uppercase; color: var(--ink-soft); margin-top: 10px; }

.grid { display: grid; gap: 28px; }
.panel { background: var(--paper-alt); border: 1px solid var(--rule);
         border-radius: 14px; padding: 26px; }
.rule { height: 1px; background: var(--rule); }
.accent { color: var(--accent); }

table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 12px; font-weight: 700; letter-spacing: .1em;
     text-transform: uppercase; color: var(--ink-soft);
     padding: 0 12px 10px 0; border-bottom: 1px solid var(--rule); }
td { padding: 13px 12px 13px 0; border-bottom: 1px solid var(--rule); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }

.note { font-size: 13px; color: var(--ink-soft); }
.flag { color: var(--brand-red); font-weight: 700; }
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_brand.py -q`
Expected: `13 passed` (11 token + 2)

- [ ] **Step 5: Commit**

```bash
git add templates/brand.css tests/test_brand.py
git commit -m "feat: design tokenek a benchmark riport mert palettajabol"
```

---

## Task 3: SVG grafikonok

**Files:**
- Create: `pipeline/charts.py`
- Test: `tests/test_charts.py`

Három charttípus fedi le a riport igényeit: napi trendvonal, vízszintes
oszlopdiagram (poszt- és kampány-összehasonlítás), és gyűrűdiagram
(organic/paid megoszlás). Mind SVG, mind a tokenekből színez.

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_charts.py`:

```python
import re
from datetime import date
from xml.etree import ElementTree

import pytest

from pipeline.charts import bar_chart, donut, line_chart

SERIES = [(date(2026, 7, day), day * 3) for day in range(1, 32)]
BARS = [("Séfünk ajánlata", 9046), ("Gambas Pil-Pil", 4142), ("Frissen", 2068)]


def _parse(svg: str):
    # Stdlib parser szándékosan: a bemenet a charts.py saját, ugyanebben a
    # tesztben generált kimenete — nincs külső entitás és nincs idegen adat.
    # A riport futásidőben soha nem parse-ol XML-t.
    return ElementTree.fromstring(svg)


@pytest.mark.parametrize(
    "svg",
    [
        line_chart(SERIES, label="Hivatkozáskattintások"),
        bar_chart(BARS, label="Elérés"),
        donut([("Fizetett", 17246), ("Organikus", 1565)], label="Elérés megoszlása"),
    ],
)
def test_output_is_well_formed_svg(svg):
    root = _parse(svg)
    assert root.tag.endswith("svg")
    assert root.get("viewBox")
    assert root.get("role") == "img"
    assert root.get("aria-label")


@pytest.mark.parametrize(
    "svg",
    [
        line_chart(SERIES, label="x"),
        bar_chart(BARS, label="x"),
        donut([("a", 3), ("b", 1)], label="x"),
    ],
)
def test_colours_come_from_tokens_not_hardcoded_hex(svg):
    """Ha az akcentus változik a brand.css-ben, a chartoknak követniük kell."""
    assert "var(--" in svg
    assert not re.search(r"#[0-9A-Fa-f]{6}", svg)


def test_line_chart_draws_one_point_per_day():
    svg = line_chart(SERIES, label="x")
    path = _parse(svg).find(".//{http://www.w3.org/2000/svg}polyline")
    assert path is not None
    assert len(path.get("points").split()) == 31


def test_bar_chart_scales_to_the_largest_value():
    svg = bar_chart(BARS, label="x")
    widths = [
        float(rect.get("width"))
        for rect in _parse(svg).iter("{http://www.w3.org/2000/svg}rect")
        if rect.get("class") == "bar"
    ]
    assert len(widths) == 3
    assert widths == sorted(widths, reverse=True)
    assert widths[0] > widths[-1]


def test_donut_segments_cover_the_full_circle():
    svg = donut([("a", 3), ("b", 1)], label="x")
    circles = [
        c
        for c in _parse(svg).iter("{http://www.w3.org/2000/svg}circle")
        if c.get("class") == "segment"
    ]
    assert len(circles) == 2


def test_empty_data_renders_a_placeholder_not_a_crash():
    """Hiányzó adatnál üres keret és felirat — nem nulla, nem összeomlás."""
    for svg in (line_chart([], label="x"), bar_chart([], label="x"), donut([], label="x")):
        root = _parse(svg)
        assert root.tag.endswith("svg")
        assert "nincs adat" in svg


def test_single_point_series_does_not_divide_by_zero():
    svg = line_chart([(date(2026, 7, 1), 5)], label="x")
    assert _parse(svg).tag.endswith("svg")


def test_donut_with_zero_total_does_not_divide_by_zero():
    svg = donut([("a", 0), ("b", 0)], label="x")
    assert "nincs adat" in svg
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_charts.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.charts'`

- [ ] **Step 3: Írd meg a `pipeline/charts.py`-t**

```python
"""SVG grafikonok, külső chart-könyvtár nélkül.

Miért nem matplotlib vagy JS: a riport nyomtatásra és offline megnyitásra készül.
Az SVG vektoros (a PDF-ben éles marad), nulla függőség, és a színei a brand.css
tokenjeiből jönnek — ha az akcentus változik, a grafikonok követik.
"""

from datetime import date

W, H = 620, 260
PAD_L, PAD_R, PAD_T, PAD_B = 8, 8, 18, 26

SERIES_TOKENS = ["var(--accent)", "var(--brand-rose)", "var(--brand-blue)",
                 "var(--brand-sun)", "var(--brand-pink)"]


def _open(label: str, width: int = W, height: int = H) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{_escape(label)}" class="chart">'
    )


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _empty(label: str, width: int = W, height: int = H) -> str:
    return (
        _open(label, width, height)
        + f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" '
        'fill="none" stroke="var(--rule)"/>'
        f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" '
        'font-size="14" fill="var(--ink-soft)">nincs adat</text></svg>'
    )


def line_chart(points: list[tuple[date, float]], label: str) -> str:
    """Napi idősor. Egyetlen pontnál vízszintes vonalat rajzol, nem oszt nullával."""
    if not points:
        return _empty(label)

    values = [value for _, value in points]
    top = max(values) or 1
    span = max(len(points) - 1, 1)
    inner_w = W - PAD_L - PAD_R
    inner_h = H - PAD_T - PAD_B

    coords = []
    for index, value in enumerate(values):
        x = PAD_L + inner_w * index / span
        y = PAD_T + inner_h * (1 - value / top)
        coords.append(f"{x:.1f},{y:.1f}")

    area = (
        f'M{PAD_L},{PAD_T + inner_h} L' + " L".join(coords)
        + f' L{PAD_L + inner_w},{PAD_T + inner_h} Z'
    )

    return "".join(
        [
            _open(label),
            f'<path d="{area}" fill="var(--accent)" opacity=".12"/>',
            f'<polyline points="{" ".join(coords)}" fill="none" '
            'stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>',
            f'<line x1="{PAD_L}" y1="{PAD_T + inner_h}" x2="{PAD_L + inner_w}" '
            f'y2="{PAD_T + inner_h}" stroke="var(--rule)"/>',
            f'<text x="{PAD_L}" y="{H - 6}" font-size="12" fill="var(--ink-soft)">'
            f'{_escape(points[0][0].strftime("%m.%d."))}</text>',
            f'<text x="{PAD_L + inner_w}" y="{H - 6}" text-anchor="end" font-size="12" '
            f'fill="var(--ink-soft)">{_escape(points[-1][0].strftime("%m.%d."))}</text>',
            f'<text x="{PAD_L}" y="{PAD_T - 4}" font-size="12" fill="var(--ink-soft)">'
            f'max {int(top):,}</text>'.replace(",", " "),
            "</svg>",
        ]
    )


def bar_chart(items: list[tuple[str, float]], label: str) -> str:
    """Vízszintes oszlopok, értékkel a végükön."""
    if not items:
        return _empty(label)

    top = max(value for _, value in items) or 1
    row = 46
    height = PAD_T + row * len(items) + 10
    track = W - 210

    parts = [_open(label, W, height)]
    for index, (name, value) in enumerate(items):
        y = PAD_T + row * index
        width = max(track * value / top, 2)
        parts.append(
            f'<text x="0" y="{y + 15}" font-size="13" fill="var(--ink-soft)">'
            f"{_escape(name[:34])}</text>"
            f'<rect class="bar" x="0" y="{y + 22}" width="{width:.1f}" height="14" '
            'rx="7" fill="var(--accent)"/>'
            f'<text x="{width + 10:.1f}" y="{y + 34}" font-size="13" font-weight="700" '
            f'fill="var(--ink)">{int(value):,}</text>'.replace(",", " ")
        )
    parts.append("</svg>")
    return "".join(parts)


def donut(parts: list[tuple[str, float]], label: str) -> str:
    """Gyűrűdiagram `stroke-dasharray`-jel — nincs szükség ív-matematikára."""
    total = sum(value for _, value in parts)
    if not parts or total <= 0:
        return _empty(label, 300, 300)

    radius, circumference = 60, 2 * 3.141592653589793 * 60
    offset = 0.0
    segments = []
    legend = []

    for index, (name, value) in enumerate(parts):
        share = value / total
        length = circumference * share
        token = SERIES_TOKENS[index % len(SERIES_TOKENS)]
        segments.append(
            f'<circle class="segment" cx="150" cy="140" r="{radius}" fill="none" '
            f'stroke="{token}" stroke-width="34" '
            f'stroke-dasharray="{length:.2f} {circumference - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 150 140)"/>'
        )
        legend.append(
            f'<rect x="18" y="{234 + index * 22}" width="11" height="11" rx="3" '
            f'fill="{token}"/>'
            f'<text x="37" y="{244 + index * 22}" font-size="13" fill="var(--ink-soft)">'
            f"{_escape(name)} — {share * 100:.1f}%</text>"
        )

        offset += length

    return "".join(
        [_open(label, 300, 300 + 22 * len(parts))] + segments + legend + ["</svg>"]
    )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_charts.py -q`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/charts.py tests/test_charts.py
git commit -m "feat: SVG grafikonok tokenekbol szinezve, kulso lib nelkul"
```

---

## Task 4: Képbeágyazás

**Files:**
- Create: `pipeline/images.py`
- Test: `tests/test_images.py`

A kreatívok S3/Backblaze URL-eken vannak. Ezek ma élnek (ellenőrizve: HTTP 200,
`image/jpeg`), de lejárhatnak, és PDF-nyomtatáskor offline nem töltődnének be.
Ezért a build letölti, méretre csökkenti és base64-ként beágyazza őket.

**A tesztek nem használnak hálózatot.** A letöltő függvény injektálható, így a
tesztek lokális bájtokkal dolgoznak.

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_images.py`:

```python
import io

import pytest
from PIL import Image

from pipeline.images import PLACEHOLDER, embed, to_data_uri


def _jpeg(width=1200, height=900, colour=(200, 40, 160)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_data_uri_is_a_jpeg(tmp_path):
    uri = to_data_uri(_jpeg())
    assert uri.startswith("data:image/jpeg;base64,")


def test_large_image_is_downscaled():
    small = to_data_uri(_jpeg(2400, 1800), max_width=480)
    large = to_data_uri(_jpeg(2400, 1800), max_width=1600)
    assert len(small) < len(large)


def test_small_image_is_not_upscaled():
    import base64

    uri = to_data_uri(_jpeg(120, 90), max_width=480)
    raw = base64.b64decode(uri.split(",", 1)[1])
    assert Image.open(io.BytesIO(raw)).width == 120


def test_embed_uses_the_injected_fetcher(tmp_path):
    calls = []

    def fetcher(url):
        calls.append(url)
        return _jpeg()

    uris = embed(["https://example.test/a.jpg"], cache_dir=tmp_path, fetcher=fetcher)
    assert len(uris) == 1
    assert uris[0].startswith("data:image/jpeg;base64,")
    assert calls == ["https://example.test/a.jpg"]


def test_second_call_hits_the_cache(tmp_path):
    calls = []

    def fetcher(url):
        calls.append(url)
        return _jpeg()

    for _ in range(2):
        embed(["https://example.test/a.jpg"], cache_dir=tmp_path, fetcher=fetcher)
    assert len(calls) == 1, "a második futás nem tölthet le újra"


def test_failed_download_yields_a_placeholder_not_a_crash(tmp_path):
    def fetcher(url):
        raise OSError("hálózati hiba")

    uris = embed(["https://example.test/x.jpg"], cache_dir=tmp_path, fetcher=fetcher)
    assert uris == [PLACEHOLDER]


def test_unreadable_bytes_yield_a_placeholder(tmp_path):
    uris = embed(
        ["https://example.test/x.jpg"],
        cache_dir=tmp_path,
        fetcher=lambda url: b"nem kep",
    )
    assert uris == [PLACEHOLDER]


@pytest.mark.network
def test_real_creative_url_is_reachable():
    """Opcionális: a valós kreatív-URL-ek elérhetősége. `-m network` kapcsolóval fut."""
    from pipeline.images import fetch

    raw = fetch(
        "https://s3.eu-central-1.amazonaws.com/zoomsphere-files/"
        "prod/publisher/2026/d1110827-ba6b-4636-834d-3484893f1543.jpg"
    )
    assert raw and len(raw) > 1000
```

- [ ] **Step 2: Vedd fel a `network` markert**

`pyproject.toml`, a `[tool.pytest.ini_options]` szakaszban:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not network'"
markers = ["network: hálózatot igényel, alapból kihagyva"]
```

- [ ] **Step 3: Futtasd, hogy elbukjon**

Run: `pytest tests/test_images.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.images'`

- [ ] **Step 4: Írd meg a `pipeline/images.py`-t**

```python
"""Kreatívok letöltése és beágyazása.

A kész riport egyetlen önálló HTML fájl: e-mailben küldhető, offline megnyitható,
és PDF-be nyomtatva is hibátlan. Ezért minden kép base64 data URI-ként kerül bele,
nem külső hivatkozásként.

A letöltések a hónap mappájában cache-elődnek, így az újrarenderelés (review-kör)
nem tölt le újra semmit.
"""

import base64
import hashlib
import io
from pathlib import Path
from typing import Callable

from PIL import Image

MAX_WIDTH = 480
QUALITY = 82
TIMEOUT = 30

# Semleges helyőrző, ha egy kép nem tölthető le. Szándékosan felismerhető:
# a riportban látszania kell, hogy itt kép lett volna.
PLACEHOLDER = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3">'
            '<rect width="4" height="3" fill="#E4E0D8"/>'
            '<text x="2" y="1.7" text-anchor="middle" font-size=".32" '
            'fill="#6B665D">kép nem elérhető</text></svg>'
        ).encode("utf-8")
    ).decode("ascii")
)


def fetch(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "hello-reporting"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def to_data_uri(raw: bytes, max_width: int = MAX_WIDTH) -> str:
    image = Image.open(io.BytesIO(raw))
    image = image.convert("RGB")
    if image.width > max_width:
        height = round(image.height * max_width / image.width)
        image = image.resize((max_width, height), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=QUALITY, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def embed(
    urls: list[str],
    cache_dir: Path,
    fetcher: Callable[[str], bytes] = fetch,
    max_width: int = MAX_WIDTH,
) -> list[str]:
    """Minden URL-ből data URI. Ami nem tölthető le, helyőrzőt kap."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    results = []

    for url in urls:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        cached = cache / f"{key}.txt"
        if cached.exists():
            results.append(cached.read_text(encoding="ascii"))
            continue
        try:
            uri = to_data_uri(fetcher(url), max_width=max_width)
        except Exception:
            results.append(PLACEHOLDER)
            continue
        cached.write_text(uri, encoding="ascii")
        results.append(uri)

    return results
```

- [ ] **Step 5: Futtasd**

Run: `pytest tests/test_images.py -q`
Expected: `7 passed, 1 deselected`

- [ ] **Step 6: Ellenőrizd a valós URL-eket is egyszer**

Run: `pytest tests/test_images.py -m network -q`
Expected: `1 passed, 7 deselected`

Ha ez elbukik, **az nem a kód hibája** — azt jelenti, hogy a ZoomSphere kreatív-URL-jei
lejártak. Ilyenkor a riportban helyőrzők jelennek meg, és a menedzsernek friss
exportot kell húznia. Jelezd, ne javítsd el.

- [ ] **Step 7: Commit**

```bash
git add pipeline/images.py tests/test_images.py pyproject.toml
git commit -m "feat: kreativok letoltese, meretezese es base64 beagyazasa"
```

---

## Task 5: Asset-beágyazás és Jinja-környezet

**Files:**
- Create: `pipeline/assets.py`
- Create: `templates/print.css`
- Test: `tests/test_assets.py` (bővítés)

- [ ] **Step 1: Írd meg a `templates/print.css`-t**

```css
/* Nyomtatás: minden szekció egy 16:9-es oldal, ahogy a benchmark riportban. */

@page {
  size: 1440px 810px;
  margin: 0;
}

@media print {
  body { background: var(--paper); }
  .page {
    margin: 0;
    page-break-after: always;
    break-after: page;
    box-shadow: none;
  }
  .page:last-child { page-break-after: auto; break-after: auto; }
  .no-print { display: none !important; }
  a { text-decoration: none; color: inherit; }
}

@media screen {
  .page { box-shadow: 0 2px 24px rgba(0, 0, 0, .07); }
}

.pdf-button {
  position: fixed; top: 18px; right: 18px; z-index: 10;
  font-family: var(--font); font-size: 14px; font-weight: 700;
  padding: 11px 18px; border-radius: 999px; cursor: pointer;
  color: var(--ink); background: var(--accent); border: none;
}
```

- [ ] **Step 2: Írd meg a failing tesztet** — fűzd a `tests/test_assets.py` végéhez:

```python
def test_stylesheet_inlines_the_fonts_as_data_uris():
    from pipeline.assets import stylesheet

    css = stylesheet()
    assert "__FONT_REGULAR__" not in css, "a helyőrzőket ki kell cserélni"
    assert css.count("data:font/woff2;base64,") == 4
    assert "@page" in css, "a print.css-nek is benne kell lennie"


def test_stylesheet_has_no_external_reference():
    """A kész riport offline is működik."""
    from pipeline.assets import stylesheet

    css = stylesheet()
    assert "http://" not in css and "https://" not in css
```

- [ ] **Step 3: Futtasd, hogy elbukjon**

Run: `pytest tests/test_assets.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.assets'`

- [ ] **Step 4: Írd meg a `pipeline/assets.py`-t**

```python
"""A stíluslap és a fontok beágyazása egyetlen, önálló CSS-blokkba."""

import base64
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
TEMPLATES = ROOT / "templates"

FONT_SLOTS = {
    "__FONT_REGULAR__": "OpenSauceOne-Regular.woff2",
    "__FONT_MEDIUM__": "OpenSauceOne-Medium.woff2",
    "__FONT_BOLD__": "OpenSauceOne-Bold.woff2",
    "__FONT_BLACK__": "OpenSauceOne-Black.woff2",
}


def _data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:font/woff2;base64,{encoded}"


@lru_cache(maxsize=1)
def stylesheet() -> str:
    """brand.css + print.css, a fontokkal beágyazva."""
    css = (TEMPLATES / "brand.css").read_text(encoding="utf-8")
    for slot, filename in FONT_SLOTS.items():
        css = css.replace(slot, _data_uri(FONTS / filename))
    css += "\n" + (TEMPLATES / "print.css").read_text(encoding="utf-8")
    return css
```

- [ ] **Step 5: Futtasd**

Run: `pytest tests/test_assets.py -q`
Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add pipeline/assets.py templates/print.css tests/test_assets.py
git commit -m "feat: font- es stiluslap-beagyazas, print.css 16:9-re"
```

---

## Task 6: A riport sablonja

**Files:**
- Create: `templates/report.html.j2`
- Create: `pipeline/render.py`
- Test: `tests/test_render.py`

A sablon **kizárólag a `report_data.json`-ból** dolgozik. A narratíva-blokkok
(3. terv) egyelőre nincsenek — az ezekre épülő oldalak **kimaradnak**, nem
töltődnek ki helykitöltő szöveggel.

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_render.py`:

```python
import json
import re
from pathlib import Path

import pytest

from pipeline.render import render

GOLDEN = (
    Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
)


@pytest.fixture
def data():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture
def html(data, tmp_path):
    return render(data, cache_dir=tmp_path, fetcher=lambda url: b"")


def test_report_is_a_single_self_contained_file(html):
    """Se külső kép, se külső font, se külső script."""
    assert "<html" in html and "</html>" in html
    assert not re.search(r'(src|href)="https?://', html)


def test_every_section_is_a_16_by_9_page(html):
    assert html.count('class="page') >= 8


def test_cover_shows_client_and_period(html):
    assert "Larus Étterem" in html
    assert "2026" in html


def test_key_numbers_appear(html):
    assert "4 312" in html or "4312" in html
    assert "130" in html
    assert "472" in html


def test_unmatched_boosts_are_disclosed(html):
    """Ami nem mérhető, azt a riport kimondja — nem hallgatja el."""
    assert "nem illesztett" in html.lower() or "nem párosított" in html.lower()


def test_narrative_sections_are_omitted_without_narrative(html):
    """A 3. terv előtt nincs narratíva — helykitöltő szöveg sem lehet."""
    assert "Lorem" not in html
    assert "TODO" not in html


def test_numbers_use_hungarian_thousand_separator(html):
    assert "18 811" in html or "18&nbsp;811" in html


def test_render_is_deterministic(data, tmp_path):
    first = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    second = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")
    assert first == second
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_render.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.render'`

- [ ] **Step 3: Írd meg a `pipeline/render.py`-t**

```python
"""A riport összeállítása. Csak a `report_data.json`-t olvassa, forrásfájlt soha."""

from datetime import date
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline import charts, images
from pipeline.assets import TEMPLATES, stylesheet

MONTHS_HU = [
    "január", "február", "március", "április", "május", "június",
    "július", "augusztus", "szeptember", "október", "november", "december",
]


def _number(value, digits: int = 0) -> str:
    """Magyar ezres elválasztó: nem törhető szóköz."""
    if value is None:
        return "–"
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def _money(value, currency: str) -> str:
    return f"{_number(value, 2)} {currency}"


def _period_hu(period: str) -> str:
    year, month = period.split("-")
    return f"{year}. {MONTHS_HU[int(month) - 1]}"


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = _number
    env.filters["money"] = _money
    return env


def render(
    data: dict,
    cache_dir: Path,
    narrative: dict | None = None,
    fetcher: Callable[[str], bytes] = images.fetch,
) -> str:
    posts = sorted(data["posts"], key=lambda post: -post["reach"])

    for post in posts:
        uris = images.embed(post["creatives"][:1], cache_dir=cache_dir, fetcher=fetcher)
        post["thumb"] = uris[0] if uris else images.PLACEHOLDER

    cross = data["cross"]
    paid = data["paid"]

    reach_split = charts.donut(
        [
            ("Boostolt posztok", cross["post_reach_sum"] - _organic_reach(posts)),
            ("Organikus posztok", _organic_reach(posts)),
        ],
        label="A poszt-elérés megoszlása",
    )
    top_bars = charts.bar_chart(
        [(post["caption"][:34] or "(nincs szöveg)", post["reach"]) for post in posts[:6]],
        label="A hat legnagyobb elérésű poszt",
    )

    template = _environment().get_template("report.html.j2")
    return template.render(
        data=data,
        posts=posts,
        page_fields=sorted(
            {field for fields in data["page"].values() for field in fields}
        ),
        narrative=narrative,
        css=stylesheet(),
        period_hu=_period_hu(data["meta"]["period"]),
        generated=date.today().isoformat(),
        charts={"reach_split": reach_split, "top_posts": top_bars},
        currency=paid["currency"],
    )


def _organic_reach(posts: list[dict]) -> int:
    return sum(post["reach"] for post in posts if post.get("paid") is None)
```

- [ ] **Step 4: Írd meg a `templates/report.html.j2`-t**

```jinja
<!doctype html>
<html lang="{{ data.meta.language }}">
<head>
<meta charset="utf-8">
<title>{{ data.meta.client }} — {{ period_hu }} riport</title>
<style>{{ css }}</style>
</head>
<body>

<button class="pdf-button no-print" onclick="window.print()">Letöltés PDF-ként</button>

<section class="page" style="justify-content:flex-end">
  <div class="eyebrow">HELLO Agency · Social media riport</div>
  <h1>{{ data.meta.client }}</h1>
  <h2 style="color:var(--ink-soft);font-weight:500;margin-top:14px">{{ period_hu }}</h2>
</section>

<section class="page">
  <div class="eyebrow">Áttekintés</div>
  <h2 style="margin-bottom:44px">A hónap számokban</h2>
  <div class="grid" style="grid-template-columns:repeat(4,1fr)">
    <div>
      <div class="stat">{{ data.content.total }}</div>
      <div class="stat-label">kiküldött tartalom</div>
    </div>
    <div>
      <div class="stat">{{ data.cross.post_reach_sum | num }}</div>
      <div class="stat-label">poszt-elérés összesen</div>
    </div>
    <div>
      <div class="stat">{{ data.paid.spend | money(currency) }}</div>
      <div class="stat-label">hirdetési költés</div>
    </div>
    <div>
      <div class="stat accent">{{ data.cross.reach_multiplier }}×</div>
      <div class="stat-label">boostolt / organikus elérés</div>
    </div>
  </div>
  <p class="note" style="margin-top:auto">
    A poszt-elérés a hónap posztjainak elérés-összege. Nem azonos a havi
    egyedi eléréssel: aki több posztot is látott, itt többször szerepel.
  </p>
</section>

<section class="page">
  <div class="eyebrow">Mit csináltunk</div>
  <h2 style="margin-bottom:40px">A hónap tartalma</h2>
  <div class="grid" style="grid-template-columns:repeat({{ data.content.by_type | length }},1fr)">
    {% for kind, count in data.content.by_type.items() %}
    <div class="panel">
      <div class="stat">{{ count }}</div>
      <div class="stat-label">{{ kind }}</div>
    </div>
    {% endfor %}
  </div>
  {% if data.content.stories_by_channel %}
  <p style="margin-top:32px">
    Story-k csatornánként:
    {% for channel, count in data.content.stories_by_channel.items() %}
    <strong>{{ channel }} {{ count }}</strong>{{ "" if loop.last else " · " }}
    {% endfor %}
  </p>
  {% endif %}
</section>

<section class="page">
  <div class="eyebrow">Oldal-teljesítmény</div>
  <h2 style="margin-bottom:36px">Csatornánkénti összesítés</h2>
  <table>
    <tr><th>Csatorna</th>
      {% for field in page_fields %}<th class="num">{{ field }}</th>{% endfor %}
    </tr>
    {% for channel, fields in data.page.items() %}
    <tr><td><strong>{{ channel }}</strong></td>
      {% for field in page_fields %}
      <td class="num">{{ fields.get(field) | num }}</td>
      {% endfor %}
    </tr>
    {% endfor %}
  </table>
  <p class="note" style="margin-top:auto">
    Ezek oldal-szintű összegek, és a fizetett aktivitás eredményét is tartalmazzák —
    nem tisztán organikus értékek.
  </p>
</section>

<section class="page">
  <div class="eyebrow">Top posztok</div>
  <h2 style="margin-bottom:30px">A hónap legjobban teljesítő tartalmai</h2>
  <div class="grid" style="grid-template-columns:repeat(3,1fr)">
    {% for post in posts[:3] %}
    <div class="panel">
      <img src="{{ post.thumb }}" alt="" style="width:100%;border-radius:8px">
      <p style="margin-top:14px;color:var(--ink)">{{ post.caption[:90] }}</p>
      <div class="rule" style="margin:14px 0"></div>
      <p><strong>{{ post.reach | num }}</strong> elérés ·
         {{ post.reactions | num }} reakció</p>
      {% if post.paid %}
      <p class="accent"><strong>ebből fizetett:</strong>
         {{ post.paid.spend | money(currency) }} → {{ post.paid.reach | num }} elérés</p>
      {% else %}
      <p class="note">tisztán organikus</p>
      {% endif %}
    </div>
    {% endfor %}
  </div>
</section>

<section class="page">
  <div class="eyebrow">Top posztok</div>
  <h2 style="margin-bottom:30px">Elérés szerinti sorrend</h2>
  {{ charts.top_posts | safe }}
</section>

<section class="page">
  <div class="eyebrow">Fizetett hirdetés</div>
  <h2 style="margin-bottom:36px">Kampányok eredménytípus szerint</h2>
  <table>
    <tr><th>Eredménytípus</th><th class="num">Kampány</th>
        <th class="num">Költés</th><th class="num">Eredmény</th></tr>
    {% for kind, block in data.paid.by_result_type.items() %}
    <tr>
      <td>{{ kind }}</td>
      <td class="num">{{ block.campaigns }}</td>
      <td class="num">{{ block.spend | money(currency) }}</td>
      <td class="num">{{ block.results | num }}</td>
    </tr>
    {% endfor %}
  </table>
  <p class="note" style="margin-top:auto">
    Az eredménytípusok külön sorokban szerepelnek, mert mást mérnek — összegük
    nem értelmezhető.
  </p>
</section>

<section class="page">
  <div class="eyebrow">Organikus és fizetett</div>
  <h2 style="margin-bottom:24px">Mennyit ér a boost</h2>
  <div class="grid" style="grid-template-columns:1fr 1fr;align-items:center">
    <div>{{ charts.reach_split | safe }}</div>
    <div>
      <div class="stat">{{ data.cross.avg_reach_organic_post | num }}</div>
      <div class="stat-label">organikus poszt átlagos elérése</div>
      <div class="stat accent" style="margin-top:34px">
        {{ data.cross.avg_reach_boosted_post | num }}</div>
      <div class="stat-label">boostolt poszt átlagos elérése</div>
      <p style="margin-top:28px">
        {{ data.cross.posts_boosted }} boostolt poszt
        {{ data.cross.boost_spend | money(currency) }} költéssel a havi poszt-elérés
        <strong>{{ (data.cross.boosted_share_of_post_reach * 100) | num(1) }}%-át</strong> adta.
      </p>
    </div>
  </div>
</section>

<section class="page">
  <div class="eyebrow">Módszertan</div>
  <h2 style="margin-bottom:30px">Mit mértünk, és mit nem</h2>
  <p style="max-width:900px">
    Minden szám a Meta és a ZoomSphere hivatalos exportjaiból származik, számítással,
    becslés nélkül. A riport {{ data.quality.posts_total }} posztot dolgozott fel,
    ebből {{ data.quality.posts_with_creative }} párosult a tartalomnaptár kreatívjával.
  </p>
  {% if data.quality.unmatched_boosts %}
  <div class="panel" style="margin-top:28px">
    <h3 class="flag">{{ data.quality.unmatched_boosts | length }} boostolt hirdetés nem
      illesztett</h3>
    <p style="margin-top:10px">
      Ezekhez nem állt rendelkezésre a megfelelő tartalom-export, ezért a
      költésük nem jelenik meg poszt szinten. Nem becsültük meg.
    </p>
    <ul style="margin-top:12px;padding-left:20px">
      {% for name in data.quality.unmatched_boosts %}
      <li>{{ name[:90] }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}
  <p class="note" style="margin-top:auto">
    A havi egyedi elérés (reach) nem számítható részadatokból, ezért ez a riport
    nem közöl ilyen számot. Készült: {{ generated }}.
  </p>
</section>

<section class="page" style="justify-content:flex-end">
  <h2>Beszéljünk arról, mi jön ezután.</h2>
  <p style="margin-top:22px">+36 1 365 1788 · agency@helloagency.hu · helloagency.hu</p>
  <div class="eyebrow" style="margin-top:36px">HELLO Agency</div>
</section>

</body>
</html>
```

- [ ] **Step 5: Futtasd**

Run: `pytest tests/test_render.py -q`
Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add pipeline/render.py templates/report.html.j2 tests/test_render.py
git commit -m "feat: 16:9 HTML riport sablon, csak a report_data-bol"
```

---

## Task 7: CLI-integráció és élő ellenőrzés

**Files:**
- Modify: `pipeline/cli.py`
- Test: `tests/test_cli.py` (bővítés)

- [ ] **Step 1: Írd meg a failing tesztet** — fűzd a `tests/test_cli.py` végéhez:

```python
def test_render_writes_the_html(fixture_dir, tmp_path):
    target = tmp_path / "Riport.html"
    exit_code = main(
        [
            str(fixture_dir), "--period", "2026-07",
            "--out", str(tmp_path / "report_data.json"),
            "--html", str(target),
            "--offline",
        ]
    )
    assert exit_code == 0
    html = target.read_text(encoding="utf-8")
    assert "Larus Étterem" in html
    assert html.startswith("<!doctype html>")


def test_validate_does_not_render(fixture_dir, tmp_path):
    target = tmp_path / "Riport.html"
    main([str(fixture_dir), "--period", "2026-07", "--validate", "--html", str(target)])
    assert not target.exists()
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_cli.py -q`
Expected: FAIL — `unrecognized arguments: --html`

- [ ] **Step 3: Bővítsd a `pipeline/cli.py`-t**

Az `argparse` blokkba:

```python
    parser.add_argument("--html", default=None, help="Riport.html útvonala")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="ne töltsön le képet — a kreatívok helyén helyőrző jelenik meg",
    )
```

A `--validate` ág után, a `report_data.json` írása alá:

```python
        from pipeline import images
        from pipeline.render import render

        html_path = Path(args.html or Path(args.directory) / "Riport.html")
        fetcher = (lambda url: b"") if args.offline else images.fetch
        html_path.write_text(
            render(
                data,
                cache_dir=Path(args.directory) / ".image-cache",
                fetcher=fetcher,
            ),
            encoding="utf-8",
        )
        print(f"→ {html_path}")
```

- [ ] **Step 4: Futtasd a teljes készletet**

Run: `pytest -q`
Expected: `132 passed, 1 deselected`

*(83 az 1. tervből + 5 font + 13 token + 12 chart + 7 kép + 2 asset + 8 render + 2 CLI.
Ha az összeg eltér, a különbséget nevezd meg — ne igazítsd a számot a méréshez.)*

- [ ] **Step 5: Generáld le a valódi riportot, képekkel**

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 \
  --out /tmp/report_data.json --html /tmp/Riport.html
```

Nyisd meg a `/tmp/Riport.html`-t böngészőben, és **nézd meg a saját szemeddel**:

- [ ] tíz 16:9-es oldal, egymás alatt
- [ ] Open Sauce One betűtípus (nem rendszerfont)
- [ ] a Top posztok oldalon **valódi kreatív-képek**, nem helyőrzők
- [ ] `Ctrl+P` → az előnézetben oldalanként egy szekció, nem elcsúszva
- [ ] a fájlméret 8 MB alatt

Ha a képek helyőrzők, futtasd: `pytest tests/test_images.py -m network -q`.
Ha az elbukik, a kreatív-URL-ek jártak le — jelezd, ne kerüld meg.

- [ ] **Step 6: Commit**

```bash
git add pipeline/cli.py tests/test_cli.py
git commit -m "feat: --html es --offline kapcsolo a CLI-ben"
```

---

## Task 8: A spec szinkronizálása

**Files:**
- Modify: `docs/superpowers/specs/2026-08-05-hello-reporting-design.md`

- [ ] **Step 1: A 8.2 szakaszban rögzítsd a font tényleges forrását**

A `marcologous/Open-Sauce-Fonts` repóban **csak TTF van**, woff2 nincs — ezért
a `tools/vendor_fonts.py` konvertál, és a woff2 fájlok a repóba kerülnek.
A `fonttools` fejlesztői függőség, a menedzsernek nem kell.

- [ ] **Step 2: A 8.4 szakaszban javítsd a charttípusok listáját**

A v1-ben három típus készült el: **vonal, vízszintes oszlop, gyűrű**.
A halmozott sáv nem készült el — nem volt rá szükség.

- [ ] **Step 3: A 14. szakasz teszt-táblájába vedd fel**

| Teszt | Mit rögzít |
|---|---|
| Design tokenek | mind a 11 token a mért értéket tartalmazza |
| Chart-színek | az SVG-kben nincs beégetett hex, csak `var(--…)` |
| Önállóság | a kész HTML-ben nincs `http(s)://` hivatkozás |
| Determinizmus | ugyanaz a bemenet → bájtazonos HTML |

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-05-hello-reporting-design.md
git commit -m "docs: spec szinkronizalasa a rendereles implementaciojaval"
```

---

## Mit ad ez a terv a végén

```bash
python -m pipeline.cli clients/larus/2026-07 --period 2026-07
```

→ `report_data.json` **és** `Riport.html`: tíz 16:9-es oldal, HELLO-brandelt,
valódi kreatív-képekkel, SVG grafikonokkal, beágyazott fontokkal.
Egyetlen fájl, e-mailben küldhető, offline megnyitható, egy kattintással PDF.

A riport **kimondja, amit nem tud**: a nem illesztett boostokat felsorolja, és
a módszertani oldalon leírja, hogy havi egyedi elérést nem közöl.

## Spec-lefedettség — mi marad ki tudatosan

A spec 7. szekciója 18 riportoldalt sorol fel. A 2. terv **tízet** valósít meg —
azokat, amelyekhez van adat. A többi nem elmaradás, hanem függőség:

| Spec-szekció | Státusz |
|---|---|
| 8.1–8.4 design rendszer, chartok | ✅ ebben a tervben |
| 0–2, 4–8, 10–12, 17 riportoldalak | ✅ ebben a tervben |
| 3, 13, 15, 16 (narratíva-oldalak) | 3. terv — ✍️ tartalom nélkül helykitöltő sem lehet |
| 9 (story-oldal) | ⚙️ nincs story-metrika; a kreatív-csík a 3. tervben, a wizarddal együtt |
| 14 (metrika-szótár) | 3. terv — a `references/metrics-glossary.md`-ből épül |
| 13. szekció (`client.yaml` szekció-kapcsolók) | 3. terv — a varázslóval együtt van értelme |
| 8.5 `assets/logo/`, `assets/shapes/` | ⚠️ **nyitott, lásd alább** |

### ⚠️ Nyitott: a HELLO logó és a geometriai díszelemek

A spec `assets/logo/` és `assets/shapes/` mappát ír elő. A logó a brand guide
PDF-jébe van ágyazva; onnan kinyerni bizonytalan minőségű eredményt adna, a
brand guide pedig kifejezetten tiltja a logó torzítását vagy átszabását.

**Ezért a 2. terv logó nélkül készül el** — a címlap és a záróoldal tipográfiával
dolgozik. A hiány látható és szándékos, nem csendes kihagyás.

Ahhoz, hogy bekerüljön, egy dolog kell: **az eredeti logó SVG-ben**, a
designertől. Amint megvan, egyetlen sablonmódosítás.

## Ami a 3. tervre marad

`SKILL.md` és a `references/` dokumentumok · export-varázsló a hiányzó fájlokra ·
`narrative.json` séma és a szám-ellenőrzés · a narratíva-oldalak (vezetői
összefoglaló, kulcsmegállapítás, akcióterv) · `review.js` szerkesztéssel és
megjegyzésekkel · `--apply-review`.
