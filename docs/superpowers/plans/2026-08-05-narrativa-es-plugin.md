# HELLO Reporting — 4. terv: Narratíva, plugin, review-kör

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A riport megszólal — vezetői összefoglaló, kulcsmegállapítás, akcióterv —, a menedzser egy paranccsal telepíti és futtatja, és a böngészőben át tudja írni, amit másképp mondana.

**Architecture:** Claude a lezárt `report_data.json`-t olvassa, és `narrative.json`-t ír. **A narratíva szövegében nem szerepelhet leírt szám** — csak `{cross.reach_multiplier|x}` alakú hivatkozás, amit a renderer helyettesít be. Így a hallucinált szám nem hibás lesz, hanem *lehetetlen*.

**Tech Stack:** ugyanaz. Új futásidejű függőség nincs.

**Előfeltétel:** az 1-3. terv kész (192 teszt zöld, 17 oldalas riport).

---

## A központi szabály

A projekt egésze arra épül, hogy minden szám kódból jön. A narratíva az egyetlen
pont, ahol egy nyelvi modell szöveget ír a riportba — itt a legnagyobb a kockázat,
hogy egy tetszetős, de hamis szám kikerül az ügyfélhez.

A megoldás nem utólagos ellenőrzés, hanem a lehetőség elvétele:

```json
{
  "executive_summary":
    "A boostolt posztok a havi poszt-elérés {cross.boosted_share_of_post_reach|pct}-át
     adták, {cross.boost_spend|money} költésből. Organikusan egy poszt átlagosan
     {cross.avg_reach_organic_post} embert ért el, boosttal
     {cross.avg_reach_boosted_post}-t — {cross.reach_multiplier|x} a különbség."
}
```

**A validátor elutasít minden leírt számjegyet a narratíva szövegében.** Nincs mód
számot beírni; csak hivatkozni lehet rá. Ha egy hivatkozás nem létező mezőre mutat,
a build megáll.

Ez magyarul nem kényelmetlen: „a hat legjobb poszt", „harmadik hete" — a
számnevek kiírva természetesebbek is. Ahol tényleg szám kell, ott adat van
mögötte, tehát van mire hivatkozni.

### Formázók

| Írás | Eredmény |
|---|---|
| `{cross.avg_reach_organic_post}` | `130` |
| `{paid.spend\|money}` | `472,71 EUR` |
| `{cross.boosted_share_of_post_reach\|pct}` | `91,7%` |
| `{cross.reach_multiplier\|x}` | `33,2×` |
| `{meta.period\|month}` | `2026. július` |
| `{meta.client\|raw}` | `Larus Étterem` |

---

## Fájlstruktúra

| Fájl | Felelősség |
|---|---|
| `pipeline/narrative.py` | séma, behelyettesítés, számjegy-tilalom |
| `templates/sections/narrative.html.j2` | a négy narratíva-oldal |
| `skills/hello-report/SKILL.md` | a workflow, amit Claude követ |
| `skills/hello-report/references/export-guide.md` | kattintásvezető, csak hiánynál töltődik be |
| `skills/hello-report/references/narrative-guide.md` | hangnem, mit írjon és mit ne |
| `skills/hello-report/references/metrics-glossary.md` | metrika-definíciók |
| `.claude-plugin/marketplace.json` | egyparancsos telepítés |
| `templates/review.js` | szerkesztés, megjegyzés, mentés |
| `pipeline/review.py` | `review.json` beolvasása és alkalmazása |

---

## Task 1: A narratíva-motor

**Files:** Create `pipeline/narrative.py`, `tests/test_narrative.py`; Modify `pipeline/errors.py`

- [ ] **Step 1: Vedd fel a kivételt** — `pipeline/errors.py`:

```python
class NarrativeError(PipelineError):
    """A narratíva szövege leírt számot tartalmaz, vagy nem létező mezőre hivatkozik."""
```

- [ ] **Step 2: Írd meg a failing tesztet** — `tests/test_narrative.py`:

```python
import pytest

from pipeline.errors import NarrativeError
from pipeline.narrative import BLOCKS, resolve, resolve_all

DATA = {
    "meta": {"client": "Larus Étterem", "period": "2026-07"},
    "paid": {"spend": 472.71, "currency": "EUR"},
    "cross": {
        "avg_reach_organic_post": 130,
        "avg_reach_boosted_post": 4312,
        "reach_multiplier": 33.2,
        "boosted_share_of_post_reach": 0.917,
        "boost_spend": 57.62,
    },
}


def test_plain_reference_is_formatted_hungarian():
    assert resolve("{cross.avg_reach_boosted_post} ember", DATA) == "4 312 ember".replace(
        " ", " ", 1
    )


def test_money_formatter():
    assert resolve("{paid.spend|money}", DATA) == "472,71 EUR"


def test_percentage_formatter():
    assert resolve("{cross.boosted_share_of_post_reach|pct}", DATA) == "91,7%"


def test_multiplier_formatter():
    assert resolve("{cross.reach_multiplier|x}", DATA) == "33,2×"


def test_month_formatter():
    assert resolve("{meta.period|month}", DATA) == "2026. július"


def test_raw_formatter_passes_strings_through():
    assert resolve("{meta.client|raw}", DATA) == "Larus Étterem"


def test_a_written_number_is_refused():
    """Ez a projekt legfontosabb szabálya: számot nem lehet leírni, csak hivatkozni."""
    with pytest.raises(NarrativeError, match="leírt szám"):
        resolve("A boost 33,2-szeresére növelte az elérést.", DATA)


def test_a_written_number_is_refused_even_next_to_a_reference():
    with pytest.raises(NarrativeError, match="leírt szám"):
        resolve("{cross.avg_reach_organic_post} helyett 4312 ember.", DATA)


def test_unknown_field_stops_the_build():
    with pytest.raises(NarrativeError, match="nincs ilyen mező"):
        resolve("{cross.nincs_ilyen}", DATA)


def test_unknown_formatter_stops_the_build():
    with pytest.raises(NarrativeError, match="ismeretlen formázó"):
        resolve("{paid.spend|forint}", DATA)


def test_resolve_all_walks_the_whole_structure():
    narrative = {
        "executive_summary": "{cross.reach_multiplier|x} a különbség.",
        "what_worked": ["{paid.spend|money} költés."],
        "key_finding": {"title": "Címsor", "body": "{cross.avg_reach_organic_post}"},
    }
    out = resolve_all(narrative, DATA)
    assert out["executive_summary"] == "33,2× a különbség."
    assert out["what_worked"] == ["472,71 EUR költés."]
    assert out["key_finding"]["body"] == "130"


def test_every_declared_block_is_documented():
    """A séma önmagát írja le — a SKILL.md ebből dolgozik."""
    for key, meta in BLOCKS.items():
        assert meta["label"], key
        assert meta["guidance"], f"{key}: nincs megadva, mit írjon bele"
```

- [ ] **Step 3: Futtasd, hogy elbukjon** — `pytest tests/test_narrative.py -q`

- [ ] **Step 4: Írd meg a `pipeline/narrative.py`-t**

```python
"""A narratíva-réteg: szöveg, amiben számot nem lehet leírni.

Ez az egyetlen pont, ahol nyelvi modell szöveget ír a riportba, tehát itt a
legnagyobb a kockázat, hogy egy tetszetős, de hamis szám kikerül az ügyfélhez.
A védelem nem utólagos ellenőrzés, hanem a lehetőség elvétele: a szövegben
**minden számjegy tiltott**, számra csak `{mezo.ut|formazo}` alakban lehet
hivatkozni.

Magyarul ez nem kényelmetlen: „a hat legjobb poszt" kiírva természetesebb is.
Ahol tényleg szám kell, ott adat van mögötte — tehát van mire hivatkozni.
"""

import re

from pipeline.errors import NarrativeError

REFERENCE = re.compile(r"\{([a-z_]+(?:\.[a-z_]+)*)(?:\|([a-z]+))?\}")
DIGIT = re.compile(r"\d")

MONTHS_HU = [
    "január", "február", "március", "április", "május", "június",
    "július", "augusztus", "szeptember", "október", "november", "december",
]

# A blokkok, amiket Claude ír. A `guidance` a SKILL.md-be és a
# narrative-guide.md-be kerül — a séma írja le önmagát.
BLOCKS = {
    "executive_summary": {
        "label": "Vezetői összefoglaló",
        "guidance": (
            "Három-négy mondat arról, mi történt a hónapban és miért. "
            "A legfontosabb állítással kezdj, ne a felsorolással."
        ),
    },
    "key_finding": {
        "label": "A hónap kulcsmegállapítása",
        "guidance": (
            "Egyetlen megállapítás, ami a döntést befolyásolja. "
            "`title` rövid állítás, `body` két-három mondat indoklás."
        ),
    },
    "what_worked": {
        "label": "Mi működött",
        "guidance": "Két-három pont, mindegyik konkrét tartalomra vagy kampányra mutat.",
    },
    "what_to_improve": {
        "label": "Min javítsunk",
        "guidance": (
            "Két-három pont. Ne hibáztass — azt írd le, mit csinálunk másképp."
        ),
    },
    "next_steps": {
        "label": "Következő lépések",
        "guidance": "Három-négy lépés, fontossági sorrendben, mindegyik cselekvés.",
    },
}


def _number(value, digits: int = 0) -> str:
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def _lookup(path: str, data: dict):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise NarrativeError(f"nincs ilyen mező: {path!r}")
        current = current[part]
    return current


def _format(value, formatter: str | None, data: dict) -> str:
    if formatter in (None, "num"):
        return _number(value)
    if formatter == "money":
        return f"{_number(value, 2)} {data['paid']['currency']}"
    if formatter == "pct":
        return f"{_number(float(value) * 100, 1)}%"
    if formatter == "x":
        return f"{_number(value, 1)}×"
    if formatter == "month":
        year, month = str(value).split("-")
        return f"{year}. {MONTHS_HU[int(month) - 1]}"
    if formatter == "raw":
        return str(value)
    raise NarrativeError(f"ismeretlen formázó: {formatter!r}")


def resolve(text: str, data: dict) -> str:
    """Behelyettesítés — de előbb a számjegy-tilalom."""
    without_refs = REFERENCE.sub("", text)
    if DIGIT.search(without_refs):
        found = "".join(DIGIT.findall(without_refs))
        raise NarrativeError(
            f"leírt szám a narratívában ({found!r}): {text[:80]!r}. "
            "Számot nem lehet beírni, csak hivatkozni rá: {mezo.ut|formazo}."
        )

    def replace(match: re.Match) -> str:
        return _format(_lookup(match.group(1), data), match.group(2), data)

    return REFERENCE.sub(replace, text)


def resolve_all(narrative, data: dict):
    """Rekurzívan végigmegy a narratíva teljes szerkezetén."""
    if isinstance(narrative, str):
        return resolve(narrative, data)
    if isinstance(narrative, list):
        return [resolve_all(item, data) for item in narrative]
    if isinstance(narrative, dict):
        return {key: resolve_all(value, data) for key, value in narrative.items()}
    return narrative
```

- [ ] **Step 5: Futtasd** — `pytest tests/test_narrative.py -q` → `12 passed`

- [ ] **Step 6: Commit**

```bash
git add pipeline/narrative.py pipeline/errors.py tests/test_narrative.py
git commit -m "feat: narrativa-motor - szamot nem lehet leirni, csak hivatkozni"
```

---

## Task 2: Narratíva-oldalak

**Files:** Create `templates/sections/narrative.html.j2`; Modify `pipeline/render.py`, `pipeline/build.py`, `pipeline/cli.py`, `templates/report.html.j2`; Test: append to `tests/test_render.py`

Narratíva nélkül ezek az oldalak **nem jelennek meg** — helykitöltő szöveg nincs.

- [ ] **Step 1: Írd meg a failing tesztet**

```python
NARRATIVE = {
    "executive_summary": "A boost {cross.reach_multiplier|x}-ra emelte az elérést.",
    "key_finding": {
        "title": "A boost megtérül",
        "body": "Organikusan {cross.avg_reach_organic_post} ember, boosttal "
                "{cross.avg_reach_boosted_post}.",
    },
    "what_worked": ["A séf-ajánlat vitte a legtöbb elérést."],
    "what_to_improve": ["Az Instagram-tartalom mérése hiányos."],
    "next_steps": ["Töltsük le az Instagram Tartalom exportot."],
}


def test_narrative_pages_are_absent_without_narrative(html):
    assert "Vezetői összefoglaló" not in html


def test_narrative_pages_appear_when_given(data, tmp_path):
    from pipeline.render import render

    out = render(
        data, cache_dir=tmp_path, fetcher=lambda url: b"", narrative=NARRATIVE
    )
    assert "Vezetői összefoglaló" in out
    assert "A boost megtérül" in out
    assert "33,2×-ra emelte" in out
    assert "Következő lépések" in out


def test_narrative_references_are_substituted_not_shown_raw(data, tmp_path):
    from pipeline.render import render

    out = render(
        data, cache_dir=tmp_path, fetcher=lambda url: b"", narrative=NARRATIVE
    )
    assert "{cross." not in out


def test_narrative_with_a_written_number_stops_the_build(data, tmp_path):
    from pipeline.errors import NarrativeError
    from pipeline.render import render

    with pytest.raises(NarrativeError):
        render(
            data,
            cache_dir=tmp_path,
            fetcher=lambda url: b"",
            narrative={"executive_summary": "A boost 33,2-szeresére emelte."},
        )
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: A `render()`-ben oldd fel a narratívát**

```python
    from pipeline import narrative as narrative_module

    resolved = (
        narrative_module.resolve_all(narrative, data) if narrative else None
    )
```

és add át `narrative=resolved,` néven.

- [ ] **Step 4: Írd meg a `templates/sections/narrative.html.j2`-t**

```jinja
{% if narrative.executive_summary %}
<section class="page">
  <div class="eyebrow">Vezetői összefoglaló</div>
  <h2 style="margin-bottom:36px">A hónap röviden</h2>
  <p style="font-size:26px;line-height:1.5;max-width:1000px;color:var(--ink)">
    {{ narrative.executive_summary }}
  </p>
</section>
{% endif %}

{% if narrative.key_finding %}
<section class="page" style="justify-content:center">
  <div class="eyebrow">A hónap kulcsmegállapítása</div>
  <h2 style="font-size:64px;margin:18px 0 28px;max-width:1100px">
    {{ narrative.key_finding.title }}
  </h2>
  <p style="font-size:22px;line-height:1.5;max-width:900px">
    {{ narrative.key_finding.body }}
  </p>
</section>
{% endif %}

{% if narrative.what_worked or narrative.what_to_improve %}
<section class="page">
  <div class="eyebrow">Értékelés</div>
  <h2 style="margin-bottom:36px">Mi működött, min javítsunk</h2>
  <div class="grid" style="grid-template-columns:1fr 1fr">
    <div class="panel">
      <h3 class="accent" style="margin-bottom:16px">Mi működött</h3>
      <ul style="padding-left:20px">
        {% for item in narrative.what_worked %}<li style="margin-bottom:12px">{{ item }}</li>{% endfor %}
      </ul>
    </div>
    <div class="panel">
      <h3 style="margin-bottom:16px">Min javítsunk</h3>
      <ul style="padding-left:20px">
        {% for item in narrative.what_to_improve %}<li style="margin-bottom:12px">{{ item }}</li>{% endfor %}
      </ul>
    </div>
  </div>
</section>
{% endif %}

{% if narrative.next_steps %}
<section class="page">
  <div class="eyebrow">Következő lépések</div>
  <h2 style="margin-bottom:36px">Mit csinálunk a jövő hónapban</h2>
  <ol style="padding-left:26px;font-size:20px">
    {% for item in narrative.next_steps %}
    <li style="margin-bottom:20px;color:var(--ink)">{{ item }}</li>
    {% endfor %}
  </ol>
</section>
{% endif %}
```

- [ ] **Step 5: Illeszd be a `report.html.j2`-be**

A vezetői összefoglaló és a kulcsmegállapítás a **címlap után**, a „mi működött"
és a „következő lépések" **a fizetett szekciók után, az összefoglaló elé**.
Ehhez a `narrative.html.j2`-t bontsd két includera, vagy tedd az egészet az
összefoglaló elé — ez utóbbi egyszerűbb, és a riport így is olvasható.

Válaszd az egyszerűbbet, és írd le a jelentésedben, melyiket.

- [ ] **Step 6: A `build.py` olvassa be a `narrative.json`-t**

```python
def load_narrative(directory: Path) -> dict | None:
    path = Path(directory) / "narrative.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
```

A `cli.py` adja át a `render()`-nek.

- [ ] **Step 7: Futtasd** — `pytest -q`

- [ ] **Step 8: Commit**

```bash
git add pipeline/ templates/ tests/test_render.py
git commit -m "feat: narrativa-oldalak, feloldott hivatkozasokkal"
```

---

## Task 3: A review-kör

Egyetlen `review.json` fájl tartja a kézi számokat, a szövegjavításokat és a
megjegyzéseket. Egy gomb menti mind a hármat.

**Files:** Create `pipeline/review.py`, `templates/review.js`; Modify `pipeline/manual.py`, `templates/manual.js` (törlés), `pipeline/render.py`, `pipeline/build.py`, `templates/report.html.j2`; Test: create `tests/test_review.py`

- [ ] **Step 1: Írd meg a failing tesztet** — `tests/test_review.py`:

```python
import json

from pipeline.review import apply_edits, load_review


def test_missing_file_yields_empty_sections(tmp_path):
    review = load_review(tmp_path)
    assert review == {"manual": {}, "edits": {}, "comments": []}


def test_sections_are_read(tmp_path):
    (tmp_path / "review.json").write_text(
        json.dumps(
            {
                "manual": {"reach_facebook": 92400},
                "edits": {"executive_summary": "Átírt szöveg."},
                "comments": [{"page": 12, "text": "ide kérek kördiagramot"}],
            }
        ),
        encoding="utf-8",
    )
    review = load_review(tmp_path)
    assert review["manual"]["reach_facebook"] == 92400
    assert review["edits"]["executive_summary"] == "Átírt szöveg."
    assert review["comments"][0]["page"] == 12


def test_edits_replace_narrative_blocks():
    narrative = {"executive_summary": "Eredeti.", "what_worked": ["a"]}
    edited = apply_edits(narrative, {"executive_summary": "Átírt."})
    assert edited["executive_summary"] == "Átírt."
    assert edited["what_worked"] == ["a"]


def test_edits_do_not_touch_unknown_blocks():
    """A review.json nem hozhat létre új narratíva-blokkot."""
    edited = apply_edits({"executive_summary": "a"}, {"kitalalt_blokk": "b"})
    assert "kitalalt_blokk" not in edited


def test_edited_text_still_goes_through_the_number_check():
    """A kézzel átírt szöveg sem tartalmazhat leírt számot."""
    import pytest

    from pipeline.errors import NarrativeError
    from pipeline.narrative import resolve_all

    edited = apply_edits(
        {"executive_summary": "{cross.reach_multiplier|x}"},
        {"executive_summary": "A boost 33,2-szeres."},
    )
    with pytest.raises(NarrativeError):
        resolve_all(edited, {"cross": {"reach_multiplier": 33.2}})
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: Írd meg a `pipeline/review.py`-t**

```python
"""A review-kör: amit a menedzser a böngészőben átír, ide kerül vissza.

Egyetlen fájl (`review.json`) tartja a kézi számokat, a szövegjavításokat és a
megjegyzéseket — a menedzsernek egy gombot kell megnyomnia, nem hármat.

A javított szöveg **ugyanazon a számjegy-ellenőrzésen megy át**, mint amit
Claude írt: a review-kör nem kiskapu.
"""

import json
from pathlib import Path

EMPTY = {"manual": {}, "edits": {}, "comments": []}


def load_review(directory: Path) -> dict:
    path = Path(directory) / "review.json"
    if not path.exists():
        return dict(EMPTY)
    stored = json.loads(path.read_text(encoding="utf-8"))
    return {key: stored.get(key, default) for key, default in EMPTY.items()}


def apply_edits(narrative: dict, edits: dict) -> dict:
    """Meglévő blokkok felülírása. Új blokkot a review nem hozhat létre."""
    return {
        key: edits.get(key, value) if isinstance(value, str) else value
        for key, value in narrative.items()
    }
```

- [ ] **Step 4: A `manual.py` a `review.json`-ból olvasson**

Cseréld a `load_manual` törzsét:

```python
def load_manual(directory: Path) -> dict:
    from pipeline.review import load_review

    return load_review(directory)["manual"]
```

- [ ] **Step 5: Írd meg a `templates/review.js`-t**

Töröld a `templates/manual.js`-t; ez váltja ki.

```javascript
// Szerkesztés és mentés a böngészőben. A lokális fájlba írni nem lehet, de
// letöltést indítani igen — a review.json onnan kerül a hónap mappájába.
(function () {
  var KEY = "hello-report-review";
  var stored = JSON.parse(localStorage.getItem(KEY) || "{}");
  var comments = stored.comments || [];

  function collect() {
    var manual = {};
    document.querySelectorAll("[data-manual]").forEach(function (field) {
      var raw = field.querySelector(".manual-input").textContent;
      var value = parseInt(raw.replace(/[^0-9]/g, ""), 10);
      if (!isNaN(value)) manual[field.dataset.manual] = value;
    });

    var edits = {};
    document.querySelectorAll("[data-narrative]").forEach(function (block) {
      var text = block.textContent.trim();
      if (text && text !== block.dataset.original) {
        edits[block.dataset.narrative] = text;
      }
    });

    return { manual: manual, edits: edits, comments: comments };
  }

  function remember() {
    localStorage.setItem(KEY, JSON.stringify(collect()));
  }

  document.querySelectorAll("[data-manual] .manual-input").forEach(function (input) {
    var key = input.parentElement.dataset.manual;
    if (stored.manual && stored.manual[key]) input.textContent = stored.manual[key];
    input.addEventListener("input", remember);
  });

  document.querySelectorAll("[data-narrative]").forEach(function (block) {
    block.dataset.original = block.textContent.trim();
    if (stored.edits && stored.edits[block.dataset.narrative]) {
      block.textContent = stored.edits[block.dataset.narrative];
    }
    block.setAttribute("contenteditable", "true");
    block.classList.add("editable");
    block.addEventListener("input", remember);
  });

  document.querySelectorAll(".page").forEach(function (page, index) {
    var button = document.createElement("button");
    button.className = "comment-button no-print";
    button.textContent = "megjegyzés";
    button.onclick = function () {
      var text = prompt("Megjegyzés ehhez az oldalhoz:");
      if (!text) return;
      comments.push({ page: index + 1, text: text });
      remember();
      button.textContent = "megjegyzés ✓";
    };
    page.appendChild(button);
  });

  var save = document.createElement("button");
  save.className = "pdf-button no-print";
  save.style.right = "190px";
  save.textContent = "Mentés";
  save.onclick = function () {
    var blob = new Blob([JSON.stringify(collect(), null, 2)], {
      type: "application/json",
    });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "review.json";
    link.click();
  };
  document.body.appendChild(save);
})();
```

- [ ] **Step 6: Jelöld szerkeszthetőnek a narratíva-blokkokat**

A `narrative.html.j2`-ben minden szövegblokk kapjon `data-narrative="<kulcs>"`
attribútumot. **Csak a szöveges (nem lista) blokkok** szerkeszthetők —
a listákat a v1-ben nem bontjuk elemekre.

CSS a `brand.css`-be:

```css
.editable:focus { outline: 2px solid var(--accent); outline-offset: 6px; }
.comment-button { position: absolute; bottom: 18px; right: 18px;
                  font-family: var(--font); font-size: 12px; font-weight: 700;
                  padding: 7px 12px; border-radius: 999px; cursor: pointer;
                  color: var(--ink-soft); background: var(--paper-alt);
                  border: 1px solid var(--rule); }
```

és a `print.css` `@media print` blokkjába: `.comment-button { display: none !important; }`

- [ ] **Step 7: Futtasd** — `pytest -q`

- [ ] **Step 8: Commit**

```bash
git add pipeline/ templates/ tests/test_review.py
git commit -m "feat: review-kor - szerkesztes, megjegyzes, egy mentes"
```

---

## Task 4: `--apply-review`

**Files:** Modify `pipeline/cli.py`; Test: append to `tests/test_cli.py`

- [ ] **Step 1: Írd meg a failing tesztet**

```python
def test_apply_review_writes_the_edits_into_the_narrative(fixture_dir, tmp_path):
    import json
    import shutil

    work = tmp_path / "larus"
    shutil.copytree(fixture_dir, work)
    (work / "narrative.json").write_text(
        json.dumps({"executive_summary": "Eredeti szöveg."}), encoding="utf-8"
    )
    (work / "review.json").write_text(
        json.dumps({"edits": {"executive_summary": "Átírt szöveg."}}),
        encoding="utf-8",
    )

    exit_code = main(
        [str(work), "--period", "2026-07", "--apply-review",
         "--out", str(tmp_path / "d.json"), "--html", str(tmp_path / "r.html"),
         "--offline"]
    )
    assert exit_code == 0
    narrative = json.loads((work / "narrative.json").read_text(encoding="utf-8"))
    assert narrative["executive_summary"] == "Átírt szöveg."


def test_comments_are_reported_to_the_manager(fixture_dir, tmp_path, capsys):
    import json
    import shutil

    work = tmp_path / "larus"
    shutil.copytree(fixture_dir, work)
    (work / "review.json").write_text(
        json.dumps({"comments": [{"page": 12, "text": "ide kérek kördiagramot"}]}),
        encoding="utf-8",
    )
    main(
        [str(work), "--period", "2026-07", "--apply-review",
         "--out", str(tmp_path / "d.json"), "--html", str(tmp_path / "r.html"),
         "--offline"]
    )
    assert "ide kérek kördiagramot" in capsys.readouterr().out
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

- [ ] **Step 3: Bővítsd a `cli.py`-t**

```python
    parser.add_argument(
        "--apply-review",
        action="store_true",
        help="a review.json szövegjavításait beírja a narrative.json-be",
    )
```

és a build után, a renderelés előtt:

```python
    if args.apply_review:
        from pipeline import review as review_module
        from pipeline.build import load_narrative

        stored = review_module.load_review(Path(args.directory))
        current = load_narrative(Path(args.directory)) or {}
        if stored["edits"]:
            updated = review_module.apply_edits(current, stored["edits"])
            (Path(args.directory) / "narrative.json").write_text(
                json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"{len(stored['edits'])} szövegjavítás alkalmazva.")
        for comment in stored["comments"]:
            print(f"  megjegyzés — {comment['page']}. oldal: {comment['text']}")
```

A megjegyzések **nem hajtódnak végre automatikusan** — kiíródnak, és Claude
dolgozza fel őket a SKILL.md szerint.

- [ ] **Step 4: Futtasd** — `pytest -q`

- [ ] **Step 5: Commit**

```bash
git add pipeline/cli.py tests/test_cli.py
git commit -m "feat: --apply-review, a megjegyzesek kiirasaval"
```

---

## Task 5: Referencia-dokumentumok

**Files:** Create `skills/hello-report/references/{export-guide,narrative-guide,metrics-glossary}.md`

Ezek Claude számára készülnek, nem a felhasználónak. **Csak akkor töltődnek be,
ha kellenek** — így egy sima futás nem viszi be őket a kontextusba.

- [ ] **Step 1: `export-guide.md`**

A 3.6. szakasz checklistje a specből, lépésenként, kattintás-szinten. A
részletesség lépésenként eltér: az Ads Manager-részt a menedzserek ismerik,
ott elég egy emlékeztető; a Tartalom fül és az Eredmények csempék részletes
vezetést kapnak. Minden lépésnél írd le, **mi a fájl neve nagyjából**, és hogy
**átnevezni nem kell**.

- [ ] **Step 2: `narrative-guide.md`**

A riport hangneme: **komoly, szakmai, ügyfélnek kiküldhető.** (A varázslóé
külön, könnyedebb — az a `SKILL.md`-ben él.)

Tartalmazza:
- a számjegy-tilalmat és a hivatkozás-szintaxist, példákkal
- a `BLOCKS` szótár `guidance` szövegeit
- amit kerülni kell: általánosságok („remekül teljesített"), mentegetőzés a
  hiányzó adatokért, és minden olyan állítás, amihez nincs mező a
  `report_data.json`-ben
- egy jó és egy rossz példa ugyanarra a megállapításra

- [ ] **Step 3: `metrics-glossary.md`**

A riportban szereplő metrikák definíciója magyarul, a spec 3. szakasza alapján.
Külön kiemelve, amit a legtöbben félreértenek:

- **Elérés vs. megjelenés** — az elérés egyedi emberek száma
- **Miért nem adjuk össze a napi elérést** havi elérésre
- **Az „oldal összes" nem organikus** — a fizetett aktivitás is benne van
- **Az eredménytípusok nem összeadhatók** (`reach` vs. `post_engagement`)

- [ ] **Step 4: Commit**

```bash
git add skills/
git commit -m "docs: referencia-dokumentumok a skillhez"
```

---

## Task 6: `SKILL.md` és plugin-telepítés

**Files:** Create `skills/hello-report/SKILL.md`, `.claude-plugin/marketplace.json`, `README.md`

- [ ] **Step 1: `.claude-plugin/marketplace.json`**

```json
{
  "name": "hello-reporting",
  "owner": { "name": "HELLO Agency" },
  "plugins": [
    {
      "name": "hello-report",
      "source": "./",
      "description": "Havi social media riport Meta és ZoomSphere exportokból",
      "version": "1.0.0"
    }
  ]
}
```

- [ ] **Step 2: `skills/hello-report/SKILL.md`**

Frontmatter:

```yaml
---
name: hello-report
description: >
  Havi social media riport összeállítása egy ügyfélnek a Meta és a ZoomSphere
  exportjaiból. Használd, amikor a felhasználó riportot kér egy ügyfélre és egy
  hónapra, vagy a `clients/<ugyfel>/<YYYY-MM>` mappára hivatkozik.
---
```

A workflow, amit leír:

1. **Futtasd a `--validate`-et.** Ez megmondja, mi van a mappában és mi hiányzik.
2. **Ha hiányzik forrásfájl:** töltsd be a `references/export-guide.md`-t, és
   vezesd végig a menedzsert — **könnyed, segítőkész hangnemben**, lépésenként,
   visszaigazolást várva. Ne öntsd rá az egészet egyszerre. Ha minden fájl megvan,
   ezt a dokumentumot **ne is töltsd be**.
3. **Futtasd a build-et**, és olvasd el a `report_data.json`-t.
4. **Írd meg a `narrative.json`-t** a `references/narrative-guide.md` szerint.
   **Számot ne írj le** — csak hivatkozz rá. A build elutasítja a leírt számot.
5. **Rendereld a riportot**, és mondd meg a menedzsernek, hol van.
6. **Ha a menedzser visszatér `review.json`-nal:** futtasd `--apply-review`-val,
   dolgozd fel a megjegyzéseket, és rendereld újra.

A `SKILL.md` hangneme **könnyed és segítőkész** — ez a menedzserrel folytatott
párbeszéd. A riport hangneme ettől külön, komoly; az a `narrative-guide.md`-ben él.

- [ ] **Step 3: `README.md`**

Telepítés, egy havi futás, a mappaszerkezet, és mit csinál a menedzser lépésről
lépésre. Rövid — a részletek a referencia-dokumentumokban vannak.

- [ ] **Step 4: Ellenőrizd, hogy a plugin felismerhető**

```bash
python -c "import json,pathlib; print(json.loads(pathlib.Path('.claude-plugin/marketplace.json').read_text(encoding='utf-8')))"
head -12 skills/hello-report/SKILL.md
```

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin skills README.md
git commit -m "feat: telepitheto plugin es a workflow leirasa"
```

---

## Task 7: Éles próba a Larus-adaton

**Files:** Create `tests/fixtures/larus-2026-07/narrative.json`; Test: append to `tests/test_render.py`

- [ ] **Step 1: Írj valódi narratívát a Larus júliusi adataira**

Olvasd el a `tests/fixtures/larus-2026-07/report_data.golden.json`-t, és írd meg
a `narrative.json`-t a `narrative-guide.md` szerint. Ez **nem kitalált szöveg**:
a valós adatokra kell vonatkoznia — a boost harminchármas szorzójára, a négy
Instagram-boostra, a mért és nem mért csatornák különbségére.

Ellenőrizd, hogy a build elfogadja:

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 \
  --out /tmp/d.json --html /tmp/r.html --offline
```

- [ ] **Step 2: Írj tesztet, ami a valódi narratívát validálja**

```python
def test_the_shipped_narrative_passes_the_number_check():
    """A fixture narratívája ugyanazon a szűrőn megy át, mint bármelyik másik."""
    import json
    from pathlib import Path

    from pipeline.narrative import resolve_all

    base = Path(__file__).parent / "fixtures" / "larus-2026-07"
    data = json.loads((base / "report_data.golden.json").read_text(encoding="utf-8"))
    narrative = json.loads((base / "narrative.json").read_text(encoding="utf-8"))
    resolved = resolve_all(narrative, data)
    assert resolved["executive_summary"]
```

- [ ] **Step 3: Futtasd** — `pytest -q`

- [ ] **Step 4: Commit**

---

## Task 8: Vizuális ellenőrzés

- [ ] **Step 1: Generáld le a riportot valódi képekkel és narratívával**

- [ ] **Step 2: Nyisd meg böngészőben, és nézd végig**

- [ ] 20 oldal alatt marad
- [ ] a narratíva-oldalak olvashatók, nem csordulnak túl
- [ ] a szövegben **egyetlen szám sem hibás** — vesd össze a `--validate` kimenetével
- [ ] kattints egy narratíva-blokkba: szerkeszthető, akcentusos kerettel
- [ ] írj bele, nyomj Mentést → `review.json` letöltődik, benne az `edits`
- [ ] nyomj „megjegyzés"-t egy oldalon → bekerül a `review.json`-be
- [ ] a `review.json`-t a mappába téve `--apply-review` beírja a narratívába
- [ ] `Ctrl+P`: a szerkesztő-keretek, a megjegyzés-gombok és az üres kézi mezők
      **nem látszanak**

- [ ] **Step 3: Ha bármi nem stimmel, javítsd — és írj rá tesztet**

Az előző két tervnél összesen tíz hiba derült ki ebben a lépésben. Nem formalitás.

- [ ] **Step 4: Commit**

---

## Ezzel a projekt v1-e kész

```
/plugin marketplace add hello-agency/hello-social-riport
/hello-report clients/larus/2026-07
```

→ a menedzser megkapja a kész riportot, elolvassa, átírja amit másképp mondana,
és kiküldi PDF-ben.

## Ami utána jön

**v2** — Google Ads modul (a szekció-architektúra előkészítve), és ha igény van
rá, PPTX/Canva export a 16:9-es oldalstruktúrából.

**v3** — MCP / Graph API: csak a parser-réteg cserélődik, a normalizálás, a join,
a KPI-számítás és a renderelés változatlan. Ekkor a manuális export-lépés és a
varázsló nagy része kiváltható.
