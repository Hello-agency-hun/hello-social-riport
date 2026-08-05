# HELLO Reporting — 1. terv: Adatpipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A négy Meta/ZoomSphere export beolvasása, egységes adatmodellbe normalizálása, összejoinolása és a lezárt `report_data.json` előállítása, ellenőrző kimenettel.

**Architecture:** Forrásonként külön parser, mindegyik ugyanazt a `ParsedSource` alakot adja vissza. A `detect.py` **tartalom alapján** azonosítja a fájlokat, nem fájlnév alapján. A parserek fölött a `join.py` fűzi össze a posztokat (poszt-ID és caption alapján), a `kpi.py` számol, a `guards.py` pedig megakadályozza a matematikailag hibás műveleteket (reach összegzése, eltérő eredménytípusok összeadása). Kimenet: `report_data.json` — innentől minden szám végleges.

**Tech Stack:** Python 3.12, `openpyxl` (xlsx), beépített `csv` és `zipfile`, `pyyaml` (konfiguráció), `pytest` (teszt). Nincs pandas, nincs matplotlib.

**Referencia-adat:** a valós Larus 2026-07 export-készlet. Minden join-arány és összeg, ami a tesztekben szerepel, ezen a készleten mérve lett.

---

## Fájlstruktúra

| Fájl | Felelősség |
|---|---|
| `pipeline/errors.py` | a pipeline saját kivételei — egy helyen, hogy a hívó tudja őket kezelni |
| `pipeline/textio.py` | kódolás-felismerés és szövegbeolvasás (UTF-16 BOM, `sep=,`) |
| `pipeline/detect.py` | fájlazonosítás tartalom alapján |
| `pipeline/schema.py` | adatosztályok: `Post`, `Campaign`, `DailySeries`, `ParsedSource`, `ReportData` |
| `pipeline/parsers/zoomsphere.py` | ZoomSphere Scheduler xlsx |
| `pipeline/parsers/meta_ads.py` | Meta Ads kampány CSV |
| `pipeline/parsers/meta_content.py` | Meta Tartalom CSV |
| `pipeline/parsers/meta_daily.py` | Meta Eredmények napi CSV |
| `pipeline/guards.py` | reach-őr, eredménytípus-őr, időszak- és ügyfél-keresztellenőrzés |
| `pipeline/join.py` | ZoomSphere ↔ Tartalom ↔ Ads összefűzés |
| `pipeline/kpi.py` | összegek, arányok, cross-channel mutatók |
| `pipeline/build.py` | a teljes pipeline egy függvényben, `ReportData`-t ad vissza |
| `pipeline/cli.py` | `--validate` kimenet és `report_data.json` írás |

Elv: minden parser önállóan tesztelhető, és semmit nem tud a többiről. A `join.py` az egyetlen hely, ahol a források találkoznak.

---

## Task 1: Repo-váz és tesztkörnyezet

**Files:**
- Create: `pyproject.toml`
- Create: `pipeline/__init__.py`
- Create: `pipeline/parsers/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Írd meg a pyproject.toml-t**

```toml
[project]
name = "hello-reporting"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openpyxl>=3.1",
    "pyyaml>=6.0",
    "jinja2>=3.1",
    "pillow>=10.0",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Hozd létre az üres csomagfájlokat**

```bash
mkdir -p pipeline/parsers tests
touch pipeline/__init__.py pipeline/parsers/__init__.py tests/__init__.py
```

- [ ] **Step 3: Írj egy smoke tesztet**

`tests/test_smoke.py`:

```python
def test_pipeline_importable():
    import pipeline

    assert pipeline is not None
```

- [ ] **Step 4: Telepítsd és futtasd**

Run: `pip install -e ".[dev]" && pytest -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pipeline tests
git commit -m "chore: pipeline csomagvaz es teszkornyezet"
```

---

## Task 2: Valós tesztadat bemásolása fixture-nek

A pipeline teljes egészében valós adaton épül. Ez a task másolja be a Larus 2026-07 készletet.

**Files:**
- Create: `tests/fixtures/larus-2026-07/input/` (10 fájl)
- Create: `tests/fixtures/larus-2026-07/client.yaml`
- Create: `tests/conftest.py`

- [ ] **Step 1: Másold be a forrásfájlokat**

A fájlok a felhasználó `Downloads` mappájában vannak. Windows/Git Bash:

```bash
mkdir -p tests/fixtures/larus-2026-07/input
D="$HOME/Downloads"
cp "$D/export_Larus Étterem Social media Scheduler_2026-08-05T14_11_43.966Z.xlsx" tests/fixtures/larus-2026-07/input/
cp "$D/Larus-Étterem-Kampányok-2026.-júl.-1.-2026.-júl.-31..csv"                   tests/fixtures/larus-2026-07/input/
cp "$D/Jul-01-2026_Jul-31-2026_916860337511681.csv"                                tests/fixtures/larus-2026-07/input/
cp "$D/Felkeresések.csv" "$D/Követők.csv" "$D/Interakciók.csv" "$D/Hivatkozáskattintások.csv" tests/fixtures/larus-2026-07/input/
cp "$D/Felkeresések-2.csv" "$D/Hivatkozáskattintások-2.csv" "$D/Interakciók-2.csv" "$D/Megtekintések-2.csv" tests/fixtures/larus-2026-07/input/
ls tests/fixtures/larus-2026-07/input/ | wc -l
```

Expected: `11`

- [ ] **Step 2: Írd meg a fixture client.yaml-t**

`tests/fixtures/larus-2026-07/client.yaml`:

```yaml
client:
  name: "Larus Étterem"
  fb_page_id: "100064824963030"
  fb_page_name: "Larus Étterem"
  ig_handle: "larusetterem"

report:
  language: hu
  currency: EUR

# A `Megtekintések` csempe neve nem hordoz csatorna-információt, ezért kézzel
# rendeljük hozzá. A referencia-készletben csak az IG változat lett letöltve.
daily_metric_overrides:
  "Megtekintések": ["instagram", "views"]
```

- [ ] **Step 3: Írd meg a conftest-et**

`tests/conftest.py`:

```python
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "larus-2026-07"


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURE


@pytest.fixture
def input_dir() -> Path:
    return FIXTURE / "input"


@pytest.fixture
def input_file(input_dir):
    """Fájl keresése névtöredék alapján — a tesztek ne függjenek a pontos névtől."""

    def _find(fragment: str) -> Path:
        matches = [p for p in input_dir.iterdir() if fragment in p.name]
        assert len(matches) == 1, f"{fragment}: {len(matches)} találat"
        return matches[0]

    return _find
```

- [ ] **Step 4: Ellenőrizd, hogy a fixture betöltődik**

`tests/test_smoke.py` kiegészítése:

```python
def test_fixture_present(input_dir):
    files = list(input_dir.iterdir())
    assert len(files) == 11
```

Run: `pytest -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: valos Larus 2026-07 export-keszlet fixture-kent"
```

**Megjegyzés:** a `.gitignore` a `clients/*/*/input/` mintát zárja ki, a `tests/fixtures/` nem esik bele — ez szándékos, a fixture verziókezelt.

---

## Task 3: Kivételek és szövegbeolvasás

**Files:**
- Create: `pipeline/errors.py`
- Create: `pipeline/textio.py`
- Test: `tests/test_textio.py`

- [ ] **Step 1: Írd meg a kivételeket**

`pipeline/errors.py`:

```python
class PipelineError(Exception):
    """A pipeline minden saját hibájának őse."""


class UnknownSourceError(PipelineError):
    """Nem azonosítható bemeneti fájl."""


class MissingColumnError(PipelineError):
    """Kötelező oszlop hiányzik egy forrásból."""


class PeriodMismatchError(PipelineError):
    """Egy forrás időszaka nem a riportált hónapra esik."""


class ClientMismatchError(PipelineError):
    """Egy forrás más ügyfélhez tartozik."""


class ReachSummationError(PipelineError):
    """Reach-jellegű metrika összegzése tilos — nem additív."""


class ResultTypeMixError(PipelineError):
    """Eltérő eredménytípusú kampányok összeadása tilos."""


class UnmatchedBoostError(PipelineError):
    """Boostolt poszt nem illeszthető egyetlen tartalomhoz sem."""
```

- [ ] **Step 2: Írd meg a failing tesztet**

`tests/test_textio.py`:

```python
from pipeline.textio import read_csv_rows, read_lines


def test_utf16_daily_csv_is_decoded(input_file):
    lines = read_lines(input_file("Felkeresések.csv"))
    assert lines[0].startswith("sep=")
    assert lines[1].strip('"') == "Facebook-felkeresések"


def test_utf8_csv_is_decoded(input_file):
    lines = read_lines(input_file("Kampányok"))
    assert "Kampány neve" in lines[0]


def test_blank_lines_are_dropped(input_file):
    lines = read_lines(input_file("Követők.csv"))
    assert all(line.strip() for line in lines)


def test_multiline_campaign_name_keeps_its_blank_line(input_file):
    """A kampánynév bekezdéshatára nem tűnhet el a beolvasás során."""
    names = [row["Kampány neve"] for row in read_csv_rows(input_file("Kampányok"))]
    assert any("💫

Te kit" in name for name in names)


def test_multiline_caption_paragraphs_are_not_glued(input_file):
    """Enélkül a riportban `tartunk.A többi napon` jelenne meg."""
    captions = [row["Cím"] for row in read_csv_rows(input_file("Jul-01-2026"))]
    opening = next(c for c in captions if c.startswith("Kedves Vendégeink"))
    assert "zárva tartunk.
A többi napon" in opening


def test_csv_row_count_is_unaffected_by_embedded_newlines(input_file):
    assert len(read_csv_rows(input_file("Kampányok"))) == 29
    assert len(read_csv_rows(input_file("Jul-01-2026"))) == 16
```

- [ ] **Step 3: Futtasd, hogy elbukjon**

Run: `pytest tests/test_textio.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.textio'`

- [ ] **Step 4: Írd meg a modult**

`pipeline/textio.py`:

```python
import csv
import io
from pathlib import Path

BOMS = {
    b"\xff\xfe": "utf-16",
    b"\xfe\xff": "utf-16",
    b"\xef\xbb\xbf": "utf-8-sig",
}


def detect_encoding(raw: bytes) -> str:
    """A Meta exportjai vegyesen UTF-16 LE és UTF-8 BOM-osak."""
    for bom, encoding in BOMS.items():
        if raw.startswith(bom):
            return encoding
    return "utf-8"


def read_text(path: Path) -> str:
    """A fájl teljes szövege, kódolástól függetlenül, változtatás nélkül."""
    raw = Path(path).read_bytes()
    return raw.decode(detect_encoding(raw))


def read_lines(path: Path) -> list[str]:
    """Nem üres sorok listája — fájlazonosításhoz és a napi CSV-k fejlécéhez.

    Ne használd CSV-tartalom beolvasására: az üres sorok eldobása szétvágná az
    idézőjeles, több bekezdésre tagolt mezőket. Arra `read_csv_rows` való.
    """
    return [line for line in read_text(path).splitlines() if line.strip()]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """CSV sorok szótárként.

    A nyers szöveget adja a parsernek, nem előszűrt sorokat — így a több sorra
    tagolt kampánynevek és poszt-szövegek bekezdéshatárai megmaradnak.
    """
    reader = csv.DictReader(io.StringIO(read_text(path), newline=""))
    return [{k: (v or "") for k, v in row.items()} for row in reader]
```

**Miért nem `read_lines` szolgálja ki a CSV-ket:** az üres sorok eldobása a nyers
szöveg szintjén történne, még a CSV-parser előtt. Az idézőjeles mezőkben lévő
bekezdéshatárok így eltűnnének, és a szöveg elválasztó nélkül összeragadna —
a valós adatban `zárva tartunk.A többi napon`. A sorszám nem változna, tehát a
hiba néma maradna, és a kész riportban jelenne meg az ügyfél előtt.

- [ ] **Step 5: Futtasd**

Run: `pytest tests/test_textio.py -q`
Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
git add pipeline/errors.py pipeline/textio.py tests/test_textio.py
git commit -m "feat: kodolas-felismeres es kozos szovegbeolvasas"
```

---

## Task 4: Fájlazonosítás tartalom alapján

A menedzser nem nevez át semmit — a `detect.py` a fájl tartalmából dönt.

**Files:**
- Create: `pipeline/detect.py`
- Test: `tests/test_detect.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_detect.py`:

```python
from collections import Counter

from pipeline.detect import identify, scan


def test_identifies_every_fixture_file(input_dir):
    kinds = Counter(item.kind for item in scan(input_dir))
    assert kinds == {
        "zoomsphere": 1,
        "meta_ads": 1,
        "meta_content": 1,
        "meta_daily": 8,
    }


def test_daily_metric_name_comes_from_second_line(input_file):
    item = identify(input_file("Interakciók-2.csv"))
    assert item.kind == "meta_daily"
    assert item.metric == "Interakció tartalmaknál"
    assert item.channel == "instagram"


def test_filename_is_not_used_for_identification(input_file):
    a = identify(input_file("Felkeresések.csv"))
    b = identify(input_file("Felkeresések-2.csv"))
    assert (a.metric, a.channel) == ("Facebook-felkeresések", "facebook")
    assert (b.metric, b.channel) == ("Instagram-profilfelkeresések", "instagram")


def test_unknown_daily_metric_is_reported_not_fatal(tmp_path):
    odd = tmp_path / "Valami.csv"
    odd.write_bytes('sep=,\n"Teljesen új csempe"\n"Dátum","Primary"\n'.encode("utf-16"))
    item = identify(odd)
    assert item.kind == "meta_daily"
    assert item.metric == "Teljesen új csempe"
    assert item.channel is None
```

**A `meta_daily: 8`-hoz:** a nyolcadik napi fájl a `Megtekintések-2.csv`, aminek a
metrikaneve (`Megtekintések`) nem hordoz csatorna-információt. A `detect.identify`
ezt is `meta_daily`-nek ismeri fel, csak `channel=None`-nal — a csatornát a
`client.yaml` `daily_metric_overrides` szakasza rendeli hozzá (Task 9).

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_detect.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.detect'`

- [ ] **Step 3: Írd meg a modult**

`pipeline/detect.py`:

```python
from dataclasses import dataclass
from pathlib import Path

from pipeline.textio import read_lines

DAILY_METRICS = {
    "Facebook-felkeresések": ("facebook", "visits"),
    "Facebook-követések": ("facebook", "follows"),
    "Tartalomnál végzett műveletek": ("facebook", "interactions"),
    "Facebookos hivatkozáskattintások": ("facebook", "link_clicks"),
    "Instagram-profilfelkeresések": ("instagram", "visits"),
    "Instagramos hivatkozáskattintások": ("instagram", "link_clicks"),
    "Interakció tartalmaknál": ("instagram", "interactions"),
}


@dataclass
class Source:
    path: Path
    kind: str
    metric: str | None = None
    channel: str | None = None
    field: str | None = None


def identify(path: Path) -> Source:
    path = Path(path)

    if path.suffix.lower() == ".xlsx":
        from pipeline.parsers.zoomsphere import looks_like_zoomsphere

        if looks_like_zoomsphere(path):
            return Source(path, "zoomsphere")
        return Source(path, "unknown")

    lines = read_lines(path)
    if not lines:
        return Source(path, "unknown")

    if lines[0].lower().startswith("sep="):
        metric = lines[1].strip().strip('"')
        channel, field = DAILY_METRICS.get(metric, (None, None))
        return Source(path, "meta_daily", metric=metric, channel=channel, field=field)

    header = lines[0]
    if "Kampány neve" in header:
        return Source(path, "meta_ads")
    if "Bejegyzésazonosító" in header:
        return Source(path, "meta_content")

    return Source(path, "unknown")


def scan(directory: Path) -> list[Source]:
    return [identify(p) for p in sorted(Path(directory).iterdir()) if p.is_file()]
```

- [ ] **Step 4: Írd meg a zoomsphere felismerő segédfüggvényt**

`pipeline/parsers/zoomsphere.py` (egyelőre csak ennyi):

```python
import zipfile
from pathlib import Path

REQUIRED_HEADERS = {"PostType", "FacebookPostIDs", "InstagramPostIDs"}


def looks_like_zoomsphere(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError):
        return False
    return all(header in sheet for header in REQUIRED_HEADERS)
```

- [ ] **Step 5: Futtasd**

Run: `pytest tests/test_detect.py -q`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add pipeline/detect.py pipeline/parsers/zoomsphere.py tests/test_detect.py
git commit -m "feat: fajlazonositas tartalom alapjan, nem fajlnevbol"
```

---

## Task 5: Adatmodell

**Files:**
- Create: `pipeline/schema.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_schema.py`:

```python
from datetime import date

from pipeline.schema import Campaign, ContentItem, DailySeries, Post


def test_daily_series_total_sums_values():
    series = DailySeries(
        channel="facebook",
        field="link_clicks",
        metric="Facebookos hivatkozáskattintások",
        points=[(date(2026, 7, 1), 10), (date(2026, 7, 2), 5)],
    )
    assert series.total == 15


def test_post_is_boosted_when_paid_present():
    post = Post(channel="facebook", post_id="1", published=date(2026, 7, 1))
    assert post.is_boosted is False
    post.paid = Campaign(name="Bejegyzés: „x”", spend=13.9, currency="EUR")
    assert post.is_boosted is True


def test_content_item_prefers_channel_specific_caption():
    item = ContentItem(
        published=date(2026, 7, 1),
        post_type="image",
        captions={"facebook": "FB szöveg", "instagram": "IG szöveg"},
    )
    assert item.caption("instagram") == "IG szöveg"
    assert item.caption("facebook") == "FB szöveg"
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_schema.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.schema'`

- [ ] **Step 3: Írd meg a modult**

`pipeline/schema.py`:

```python
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Campaign:
    """Egy Meta Ads kampánysor."""

    name: str
    spend: float = 0.0
    currency: str = "EUR"
    reach: int = 0
    impressions: int = 0
    frequency: float = 0.0
    link_clicks: int = 0
    results: int = 0
    result_type: str = ""
    cost_per_result: float = 0.0
    status: str = ""
    channel: str | None = None
    is_boost: bool = False


@dataclass
class ContentItem:
    """Egy ZoomSphere sor — amit kiküldtünk."""

    published: date
    post_type: str
    captions: dict[str, str] = field(default_factory=dict)
    post_ids: dict[str, str] = field(default_factory=dict)
    permalinks: dict[str, str] = field(default_factory=dict)
    creatives: dict[str, list[str]] = field(default_factory=dict)

    def caption(self, channel: str) -> str:
        return self.captions.get(channel, "")


@dataclass
class Post:
    """A join eredménye: tartalom + organic teljesítmény + fizetett háttér."""

    channel: str
    post_id: str
    published: date
    caption: str = ""
    permalink: str = ""
    post_type: str = ""
    creatives: list[str] = field(default_factory=list)
    reach: int = 0
    views: int = 0
    reactions: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    link_clicks: int = 0
    paid: Campaign | None = None

    @property
    def is_boosted(self) -> bool:
        return self.paid is not None


@dataclass
class DailySeries:
    channel: str
    field: str
    metric: str
    points: list[tuple[date, int]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(value for _, value in self.points)


@dataclass
class ParsedSource:
    """Amit minden parser visszaad — így a build egységesen kezelheti őket."""

    kind: str
    period: tuple[date, date] | None = None
    client_hints: dict[str, str] = field(default_factory=dict)
    payload: object = None
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_schema.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/schema.py tests/test_schema.py
git commit -m "feat: egyseges adatmodell"
```

---

## Task 6: ZoomSphere parser

**Files:**
- Modify: `pipeline/parsers/zoomsphere.py`
- Test: `tests/test_zoomsphere.py`

A ZoomSphere xlsx **inline stringeket** használ (nincs `sharedStrings.xml`), ezért `openpyxl`-lel olvassuk.

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_zoomsphere.py`:

```python
from collections import Counter
from datetime import date

from pipeline.parsers.zoomsphere import parse


def test_parses_all_rows(input_file):
    source = parse(input_file("Scheduler"))
    assert len(source.payload) == 29


def test_post_type_distribution(input_file):
    types = Counter(item.post_type for item in parse(input_file("Scheduler")).payload)
    assert types == {"image": 14, "story": 14, "reel": 1}


def test_period_is_july(input_file):
    source = parse(input_file("Scheduler"))
    assert source.period == (date(2026, 7, 1), date(2026, 7, 29))


def test_facebook_post_id_keeps_only_the_suffix(input_file):
    items = parse(input_file("Scheduler")).payload
    first = next(i for i in items if i.published == date(2026, 7, 1))
    assert first.post_ids["facebook"] == "1490635643107254"
    assert first.post_ids["instagram"] == "17957904336154653"


def test_creative_urls_are_split(input_file):
    items = parse(input_file("Scheduler")).payload
    first = next(i for i in items if i.published == date(2026, 7, 1))
    assert len(first.creatives["instagram"]) == 2
    assert all(url.startswith("https://") for url in first.creatives["instagram"])


def test_client_hint_carries_page_name(input_file):
    assert parse(input_file("Scheduler")).client_hints["page_name"] == "Larus Étterem"
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_zoomsphere.py -q`
Expected: FAIL — `ImportError: cannot import name 'parse'`

- [ ] **Step 3: Írd meg a parsert**

`pipeline/parsers/zoomsphere.py` — a meglévő `looks_like_zoomsphere` alá:

```python
import re
from datetime import date, datetime

from openpyxl import load_workbook

from pipeline.schema import ContentItem, ParsedSource

CHANNEL_COLUMNS = {
    "facebook": {
        "message": "FacebookMessage",
        "source": "FacebookSources",
        "ids": "FacebookPostIDs",
        "permalink": "FacebookPublicPermalinks",
        "images": ["FacebookImages", "FacebookFileUrl", "FacebookVideoUrl"],
    },
    "instagram": {
        "message": "InstagramMessage",
        "source": "InstagramSources",
        "ids": "InstagramPostIDs",
        "permalink": "InstagramPublicPermalinks",
        "images": ["InstagramImages", "InstagramFileUrl", "InstagramVideoUrl"],
    },
}


def _clean(value: str) -> str:
    """A ZoomSphere minden azonosító mögé odaírja a fiók nevét zárójelben."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", (value or "").strip())


def _post_id(raw: str) -> str:
    """FB: `oldal_poszt` → `poszt`. IG: változatlan."""
    cleaned = _clean(raw)
    return cleaned.split("_")[-1] if cleaned else ""


def _urls(value: str) -> list[str]:
    return [u.strip() for u in (value or "").split(",") if u.strip().startswith("http")]


def _parse_datetime(value: str) -> date:
    """`01.07.2026 - 11:00 AM` → date(2026, 7, 1)"""
    return datetime.strptime(value.strip(), "%d.%m.%Y - %I:%M %p").date()


def parse(path) -> ParsedSource:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    header = [str(cell or "") for cell in next(rows)]
    index = {name: position for position, name in enumerate(header)}

    items: list[ContentItem] = []
    page_name = ""

    for row in rows:
        cells = ["" if cell is None else str(cell) for cell in row]
        cells += [""] * (len(header) - len(cells))

        def column(name: str) -> str:
            return cells[index[name]] if name in index else ""

        if not column("Datetime").strip():
            continue

        item = ContentItem(
            published=_parse_datetime(column("Datetime")),
            post_type=column("PostType").strip(),
        )

        for channel, columns in CHANNEL_COLUMNS.items():
            if not column(columns["source"]).strip():
                continue
            page_name = page_name or _clean(column(columns["source"]))
            item.captions[channel] = column(columns["message"]).strip()
            item.post_ids[channel] = _post_id(column(columns["ids"]))
            item.permalinks[channel] = _clean(column(columns["permalink"]))
            creatives: list[str] = []
            for image_column in columns["images"]:
                creatives += _urls(column(image_column))
            item.creatives[channel] = creatives

        items.append(item)

    workbook.close()
    dates = sorted(item.published for item in items)
    return ParsedSource(
        kind="zoomsphere",
        period=(dates[0], dates[-1]),
        client_hints={"page_name": page_name},
        payload=items,
    )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_zoomsphere.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/parsers/zoomsphere.py tests/test_zoomsphere.py
git commit -m "feat: ZoomSphere Scheduler parser"
```

---

## Task 7: Meta Ads parser

**Files:**
- Create: `pipeline/parsers/meta_ads.py`
- Test: `tests/test_meta_ads.py`

Három sajátosság: pénznem az oszlopfejlécből, nullás sorok kiszűrése, boost/always-on szétválasztás a kampánynév prefixéből.

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_meta_ads.py`:

```python
from datetime import date

from pipeline.parsers.meta_ads import detect_currency, parse


def test_currency_is_read_from_the_header():
    assert detect_currency(["Eredmények", "Elköltött összeg (EUR)"]) == "EUR"
    assert detect_currency(["Elköltött összeg (HUF)"]) == "HUF"


def test_zero_rows_are_filtered_and_counted(input_file):
    source = parse(input_file("Kampányok"))
    assert len(source.payload.campaigns) == 13
    assert source.payload.dropped_zero_rows == 16


def test_boosts_and_always_on_are_separated(input_file):
    campaigns = parse(input_file("Kampányok")).payload.campaigns
    boosts = [c for c in campaigns if c.is_boost]
    always_on = [c for c in campaigns if not c.is_boost]
    assert len(boosts) == 8
    assert len(always_on) == 5


def test_boost_channel_comes_from_the_name_prefix(input_file):
    boosts = [c for c in parse(input_file("Kampányok")).payload.campaigns if c.is_boost]
    assert sum(1 for c in boosts if c.channel == "instagram") == 4
    assert sum(1 for c in boosts if c.channel == "facebook") == 4


def test_total_spend(input_file):
    campaigns = parse(input_file("Kampányok")).payload.campaigns
    assert round(sum(c.spend for c in campaigns), 2) == 472.71


def test_result_types_are_preserved(input_file):
    campaigns = parse(input_file("Kampányok")).payload.campaigns
    assert {c.result_type for c in campaigns} == {
        "reach",
        "actions:omni_landing_page_view",
        "profile_visit_view",
        "actions:post_engagement",
        "actions:link_click",
        "actions:click_to_call_native_call_placed",
    }


def test_period(input_file):
    assert parse(input_file("Kampányok")).period == (date(2026, 7, 1), date(2026, 7, 31))
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_meta_ads.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.parsers.meta_ads'`

- [ ] **Step 3: Írd meg a parsert**

`pipeline/parsers/meta_ads.py`:

```python
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from pipeline.errors import MissingColumnError
from pipeline.schema import Campaign, ParsedSource
from pipeline.textio import read_csv_rows

BOOST_PREFIXES = {"Instagram-bejegyzés:": "instagram", "Bejegyzés:": "facebook"}
REQUIRED = ["Kampány neve", "Eredmény jelzése", "Elérés", "Megjelenések"]


@dataclass
class AdsPayload:
    campaigns: list[Campaign] = field(default_factory=list)
    currency: str = "EUR"
    dropped_zero_rows: int = 0


def detect_currency(header: list[str]) -> str:
    for column in header:
        match = re.search(r"Elköltött összeg \(([A-Z]{3})\)", column)
        if match:
            return match.group(1)
    return "EUR"


def _number(value: str) -> float:
    value = (value or "").strip()
    try:
        return float(value)
    except ValueError:
        return 0.0


def _boost_channel(name: str) -> str | None:
    for prefix, channel in BOOST_PREFIXES.items():
        if name.startswith(prefix):
            return channel
    return None


def parse(path) -> ParsedSource:
    rows = read_csv_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Ads export")

    header = list(rows[0].keys())
    for column in REQUIRED:
        if column not in header:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")

    currency = detect_currency(header)
    spend_column = f"Elköltött összeg ({currency})"

    payload = AdsPayload(currency=currency)
    starts, ends = [], []

    for row in rows:
        starts.append(datetime.strptime(row["Jelentés kezdete"], "%Y-%m-%d").date())
        ends.append(datetime.strptime(row["Jelentés vége"], "%Y-%m-%d").date())

        spend = _number(row.get(spend_column, ""))
        impressions = int(_number(row.get("Megjelenések", "")))
        if spend == 0 and impressions == 0:
            payload.dropped_zero_rows += 1
            continue

        name = row["Kampány neve"].replace("\n", " ").strip()
        channel = _boost_channel(name)
        payload.campaigns.append(
            Campaign(
                name=name,
                spend=spend,
                currency=currency,
                reach=int(_number(row.get("Elérés", ""))),
                impressions=impressions,
                frequency=_number(row.get("Gyakoriság", "")),
                link_clicks=int(_number(row.get("Hivatkozáskattintások", ""))),
                results=int(_number(row.get("Eredmények", ""))),
                result_type=row.get("Eredmény jelzése", "").strip(),
                cost_per_result=_number(row.get("Eredményenkénti költség", "")),
                status=row.get("Kampány teljesítése", "").strip(),
                channel=channel,
                is_boost=channel is not None,
            )
        )

    return ParsedSource(
        kind="meta_ads",
        period=(min(starts), max(ends)),
        payload=payload,
    )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_meta_ads.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/parsers/meta_ads.py tests/test_meta_ads.py
git commit -m "feat: Meta Ads kampany parser penznem-detektalassal"
```

---

## Task 8: Meta Tartalom parser

**Files:**
- Create: `pipeline/parsers/meta_content.py`
- Test: `tests/test_meta_content.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_meta_content.py`:

```python
from datetime import date

from pipeline.parsers.meta_content import parse


def test_parses_all_posts(input_file):
    assert len(parse(input_file("Jul-01-2026")).payload) == 16


def test_channel_is_derived_from_the_permalink(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    assert {p.channel for p in posts} == {"facebook"}


def test_top_post_metrics(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    top = max(posts, key=lambda p: p.reach)
    assert top.caption.startswith("Séfünk ajánlata!")
    assert top.reach == 9046
    assert top.views == 11810
    assert top.link_clicks == 1027


def test_post_id_has_no_page_prefix(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    assert all("_" not in p.post_id for p in posts)


def test_client_hints_carry_page_identity(input_file):
    hints = parse(input_file("Jul-01-2026")).client_hints
    assert hints["page_id"] == "100064824963030"
    assert hints["page_name"] == "Larus Étterem"


def test_period_spans_july(input_file):
    assert parse(input_file("Jul-01-2026")).period == (
        date(2026, 7, 1),
        date(2026, 7, 31),
    )
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_meta_content.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.parsers.meta_content'`

- [ ] **Step 3: Írd meg a parsert**

`pipeline/parsers/meta_content.py`:

```python
from datetime import datetime

from pipeline.errors import MissingColumnError
from pipeline.schema import ParsedSource, Post
from pipeline.textio import read_csv_rows

REQUIRED = ["Bejegyzésazonosító", "Elérés", "Megtekintések", "Állandó hivatkozás"]


def _number(value: str) -> int:
    value = (value or "").strip()
    try:
        return int(float(value))
    except ValueError:
        return 0


def _channel(permalink: str) -> str:
    if "instagram.com" in permalink:
        return "instagram"
    return "facebook"


def parse(path) -> ParsedSource:
    rows = read_csv_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Tartalom export")

    for column in REQUIRED:
        if column not in rows[0]:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")

    posts: list[Post] = []
    hints: dict[str, str] = {}

    for row in rows:
        permalink = row.get("Állandó hivatkozás", "").strip()
        published = datetime.strptime(
            row["Közzététel időpontja"].strip(), "%m/%d/%Y %H:%M"
        ).date()
        hints.setdefault("page_id", row.get("Oldalazonosító", "").strip())
        hints.setdefault("page_name", row.get("Oldal neve", "").strip())

        posts.append(
            Post(
                channel=_channel(permalink),
                post_id=row["Bejegyzésazonosító"].strip(),
                published=published,
                caption=row.get("Cím", "").replace("\n", " ").strip(),
                permalink=permalink,
                post_type=row.get("Bejegyzés típusa", "").strip(),
                reach=_number(row.get("Elérés", "")),
                views=_number(row.get("Megtekintések", "")),
                reactions=_number(row.get("Reakciók", "")),
                comments=_number(row.get("Hozzászólások", "")),
                shares=_number(row.get("Megosztások", "")),
                clicks=_number(row.get("Összes kattintás", "")),
                link_clicks=_number(row.get("Hivatkozáskattintások", "")),
            )
        )

    dates = sorted(post.published for post in posts)
    return ParsedSource(
        kind="meta_content",
        period=(dates[0], dates[-1]),
        client_hints=hints,
        payload=posts,
    )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_meta_content.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/parsers/meta_content.py tests/test_meta_content.py
git commit -m "feat: Meta Tartalom parser poszt-szintu metrikakkal"
```

---

## Task 9: Meta napi CSV parser

**Files:**
- Create: `pipeline/parsers/meta_daily.py`
- Test: `tests/test_meta_daily.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_meta_daily.py`:

```python
import pytest

from pipeline.errors import UnknownSourceError
from pipeline.parsers.meta_daily import parse


@pytest.mark.parametrize(
    "fragment, channel, field, total",
    [
        ("Felkeresések.csv", "facebook", "visits", 1525),
        ("Követők.csv", "facebook", "follows", 5),
        ("Interakciók.csv", "facebook", "interactions", 345),
        ("Hivatkozáskattintások.csv", "facebook", "link_clicks", 1227),
        ("Felkeresések-2.csv", "instagram", "visits", 634),
        ("Hivatkozáskattintások-2.csv", "instagram", "link_clicks", 389),
        ("Interakciók-2.csv", "instagram", "interactions", 255),
    ],
)
def test_known_metrics(input_file, fragment, channel, field, total):
    series = parse(input_file(fragment)).payload
    assert (series.channel, series.field) == (channel, field)
    assert series.total == total
    assert len(series.points) == 31


def test_unknown_metric_raises_with_the_metric_name(tmp_path):
    odd = tmp_path / "Valami.csv"
    odd.write_bytes(
        'sep=,\n"Teljesen új csempe"\n"Dátum","Primary"\n"2026-07-01T00:00:00","3"\n'.encode(
            "utf-16"
        )
    )
    with pytest.raises(UnknownSourceError, match="Teljesen új csempe"):
        parse(odd)


def test_channel_override_resolves_unknown_metric(tmp_path):
    odd = tmp_path / "Valami.csv"
    odd.write_bytes(
        'sep=,\n"Teljesen új csempe"\n"Dátum","Primary"\n"2026-07-01T00:00:00","3"\n'.encode(
            "utf-16"
        )
    )
    series = parse(odd, overrides={"Teljesen új csempe": ("facebook", "views")}).payload
    assert (series.channel, series.field, series.total) == ("facebook", "views", 3)
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_meta_daily.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.parsers.meta_daily'`

- [ ] **Step 3: Írd meg a parsert**

`pipeline/parsers/meta_daily.py`:

```python
import csv
from datetime import datetime

from pipeline.detect import DAILY_METRICS
from pipeline.errors import MissingColumnError, UnknownSourceError
from pipeline.schema import DailySeries, ParsedSource
from pipeline.textio import read_lines


def parse(path, overrides: dict[str, tuple[str, str]] | None = None) -> ParsedSource:
    """A metrika kilétét a 2. sor mondja meg, nem a fájlnév."""
    lines = read_lines(path)
    if len(lines) < 3:
        raise MissingColumnError(
            f"{path}: csonka napi export — {len(lines)} sor. Várt szerkezet: "
            "`sep=,`, metrikanév, `\"Dátum\",\"Primary\"`, majd napi sorok."
        )
    metric = lines[1].strip().strip('"')

    lookup = dict(DAILY_METRICS)
    lookup.update(overrides or {})
    if metric not in lookup:
        raise UnknownSourceError(
            f"{path}: ismeretlen napi metrika — {metric!r}. "
            "Add hozzá a client.yaml `daily_metric_overrides` szakaszához."
        )
    channel, field = lookup[metric]

    points = []
    for row in csv.reader(lines[2:]):
        if len(row) < 2 or row[0].strip().strip('"') in ("", "Dátum"):
            continue
        raw_day = row[0].strip().strip('"')
        try:
            day = datetime.strptime(raw_day, "%Y-%m-%dT%H:%M:%S").date()
            value = int(float(row[1].strip().strip('"') or 0))
        except ValueError as error:
            raise MissingColumnError(
                f"{path}: értelmezhetetlen sor a(z) {metric!r} csempénél — "
                f"{row!r} ({error})"
            ) from error
        points.append((day, value))

    if not points:
        raise MissingColumnError(f"{path}: a(z) {metric!r} csempe egyetlen napi sort sem tartalmaz")

    series = DailySeries(channel=channel, field=field, metric=metric, points=points)
    days = [day for day, _ in points]
    return ParsedSource(
        kind="meta_daily",
        period=(min(days), max(days)),
        payload=series,
    )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_meta_daily.py -q`
Expected: `13 passed`

**Miért nem elég a nyers hiba:** a CLI kizárólag `PipelineError`-t fog el. Ha egy
csonka vagy elrontott export `IndexError`-t vagy `ValueError`-t dobna, a menedzser
értelmezhetetlen stack trace-t kapna a „melyik fájlt kell újra letölteni" üzenet
helyett. Ezért minden ilyen eset `MissingColumnError`-rá alakul, a fájl nevével
és a problémás sorral. A hozzá tartozó három teszt (`csonka`,
`értelmezhetetlen sor`, `egyetlen napi sort sem`) `PipelineError`-t vár.

- [ ] **Step 5: Commit**

```bash
git add pipeline/parsers/meta_daily.py tests/test_meta_daily.py
git commit -m "feat: Meta napi CSV parser, metrika a 2. sorbol"
```

---

## Task 10: Őrök — reach, eredménytípus, időszak, ügyfél

Ez a task valósítja meg a spec 11. szekciójának védelmeit. Ezek nem kényelmi funkciók: mindegyik egy konkrét, a beszélgetés során azonosított hibalehetőséget zár le.

**Files:**
- Create: `pipeline/guards.py`
- Test: `tests/test_guards.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_guards.py`:

```python
from datetime import date

import pytest

from pipeline.errors import (
    ClientMismatchError,
    PeriodMismatchError,
    ReachSummationError,
    ResultTypeMixError,
)
from pipeline.guards import (
    check_client,
    check_period,
    sum_additive,
    sum_results,
)
from pipeline.schema import Campaign


def test_reach_may_not_be_summed():
    with pytest.raises(ReachSummationError):
        sum_additive([100, 200], field="reach")


def test_additive_fields_are_summed():
    assert sum_additive([100, 200], field="link_clicks") == 300


def test_results_of_the_same_type_are_summed():
    campaigns = [
        Campaign(name="a", results=10, result_type="actions:link_click"),
        Campaign(name="b", results=5, result_type="actions:link_click"),
    ]
    assert sum_results(campaigns) == 15


def test_results_of_mixed_types_raise():
    campaigns = [
        Campaign(name="a", results=10, result_type="reach"),
        Campaign(name="b", results=5, result_type="actions:link_click"),
    ]
    with pytest.raises(ResultTypeMixError):
        sum_results(campaigns)


def test_period_inside_the_target_month_passes():
    check_period("zoomsphere", (date(2026, 7, 1), date(2026, 7, 29)), "2026-07")


def test_period_outside_the_target_month_raises():
    with pytest.raises(PeriodMismatchError, match="zoomsphere"):
        check_period("zoomsphere", (date(2026, 6, 1), date(2026, 6, 30)), "2026-07")


def test_matching_client_passes():
    check_client(
        {"page_id": "100064824963030", "page_name": "Larus Étterem"},
        {"fb_page_id": "100064824963030", "fb_page_name": "Larus Étterem"},
    )


def test_foreign_page_id_raises():
    with pytest.raises(ClientMismatchError, match="page_id"):
        check_client(
            {"page_id": "999", "page_name": "Mammut"},
            {"fb_page_id": "100064824963030", "fb_page_name": "Larus Étterem"},
        )
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_guards.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.guards'`

- [ ] **Step 3: Írd meg a modult**

`pipeline/guards.py`:

```python
from datetime import date
from typing import Iterable

from pipeline.errors import (
    ClientMismatchError,
    PeriodMismatchError,
    ReachSummationError,
    ResultTypeMixError,
)
from pipeline.schema import Campaign

NON_ADDITIVE = {"reach", "frequency", "followers_total"}


def sum_additive(values: Iterable[float], field: str) -> float:
    """Összegzés csak additív metrikákra.

    A reach egyedi emberek száma: napi vagy poszt-szintű értékek összege nem
    havi reach, mert ugyanazt az embert többször számolná. Nincs olyan
    részadatunk, amiből a helyes érték kiszámítható lenne — az kézi bevitel.
    """
    if field in NON_ADDITIVE:
        raise ReachSummationError(
            f"{field!r} nem additív metrika — összegzése hibás értéket adna. "
            "A havi értéket kézi bevitelből kell venni (page_metrics.yaml)."
        )
    return sum(values)


def sum_results(campaigns: list[Campaign]) -> int:
    """Az `Eredmények` oszlop csak azonos `Eredmény jelzése` mellett összegezhető."""
    types = {c.result_type for c in campaigns if c.result_type}
    if len(types) > 1:
        raise ResultTypeMixError(
            "eltérő eredménytípusok nem adhatók össze: " + ", ".join(sorted(types))
        )
    return sum(c.results for c in campaigns)


def check_period(kind: str, period: tuple[date, date] | None, target: str) -> None:
    """`target` formátuma `YYYY-MM`."""
    if period is None:
        return
    year, month = (int(part) for part in target.split("-"))
    for boundary in period:
        if (boundary.year, boundary.month) != (year, month):
            raise PeriodMismatchError(
                f"{kind}: a forrás időszaka {period[0]}–{period[1]}, "
                f"a riportált hónap {target}. Valószínűleg rossz fájl került a mappába."
            )


def check_client(hints: dict[str, str], config: dict[str, str]) -> None:
    pairs = [("page_id", "fb_page_id"), ("page_name", "fb_page_name")]
    for hint_key, config_key in pairs:
        found, expected = hints.get(hint_key), config.get(config_key)
        if found and expected and found != expected:
            raise ClientMismatchError(
                f"{hint_key}: a forrásban {found!r}, a client.yaml-ben {expected!r}. "
                "Más ügyfél adata került a mappába."
            )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_guards.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/guards.py tests/test_guards.py
git commit -m "feat: reach-, eredmenytipus-, idoszak- es ugyfel-orok"
```

---

## Task 11: Join

A beszélgetés legfontosabb felfedezése. Két illesztés: poszt-ID (ZoomSphere ↔ Tartalom) és caption-prefix (Tartalom ↔ Ads).

**Files:**
- Create: `pipeline/join.py`
- Test: `tests/test_join.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_join.py`:

```python
import pytest

from pipeline.errors import UnmatchedBoostError
from pipeline.join import join_posts, normalize_caption
from pipeline.parsers import meta_ads, meta_content, zoomsphere
from pipeline.schema import Campaign, Post


def test_caption_normalisation_strips_prefix_and_quotes():
    assert normalize_caption('Bejegyzés: „Séfünk ajánlata! 😎”') == "séfünk ajánlata! 😎"
    assert normalize_caption("Instagram-bejegyzés: Ennyi! 😉🥂 #larus") == "ennyi! 😉🥂 #larus"
    assert normalize_caption("Nyári napok,   terasz...") == "nyári napok, terasz"


@pytest.fixture
def joined(input_file):
    return join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    )


def test_zoomsphere_matches_15_of_16_posts(joined):
    assert len(joined.posts) == 16
    assert sum(1 for p in joined.posts if p.creatives) == 15


def test_facebook_boosts_are_matched(joined):
    boosted = [p for p in joined.posts if p.is_boosted]
    assert len(boosted) == 4


def test_instagram_boosts_are_reported_as_unmatched(joined):
    """A referencia-készletben nincs IG Tartalom export, ezért a 4 IG boost
    nem illeszthető. A pipeline ezt jelenti, nem találgat."""
    unmatched = [c.name for c in joined.unmatched_boosts]
    assert len(unmatched) == 4
    assert all(name.startswith("Instagram-bejegyzés:") for name in unmatched)


def test_boost_carries_spend_and_paid_reach(joined):
    top = max(joined.posts, key=lambda p: p.reach)
    assert top.caption.startswith("Séfünk ajánlata!")
    assert top.paid.spend == 15.95
    assert top.paid.reach == 8398


def test_boosted_posts_dominate_reach(joined):
    boosted = sum(p.reach for p in joined.posts if p.is_boosted)
    total = sum(p.reach for p in joined.posts)
    assert total == 18811
    assert round(boosted / total, 3) == 0.917


def test_unmatched_boost_is_reported_not_guessed():
    orphan = Campaign(
        name="Bejegyzés: „Ez a poszt nem létezik”",
        spend=5.0,
        channel="facebook",
        is_boost=True,
    )
    result = join_posts(content=[], items=[], campaigns=[orphan])
    assert [c.name for c in result.unmatched_boosts] == [orphan.name]

    with pytest.raises(UnmatchedBoostError, match="nem létezik"):
        join_posts(content=[], items=[], campaigns=[orphan], strict=True)
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_join.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.join'`

- [ ] **Step 3: Írd meg a modult**

`pipeline/join.py`:

```python
import re
from dataclasses import dataclass, field

from pipeline.errors import UnmatchedBoostError
from pipeline.schema import Campaign, ContentItem, Post

BOOST_PREFIX = re.compile(r"^(Instagram-bejegyzés:|Bejegyzés:)\s*")
MATCH_LENGTH = 30


@dataclass
class JoinResult:
    posts: list[Post] = field(default_factory=list)
    unmatched_boosts: list[Campaign] = field(default_factory=list)
    unmatched_content: list[Post] = field(default_factory=list)


def normalize_caption(text: str) -> str:
    """A boostolt kampány neve a poszt szövegének csonkolt változata."""
    text = BOOST_PREFIX.sub("", text or "")
    text = text.strip().strip("„”\"'")
    text = text.replace("…", "").replace("...", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def join_posts(
    content: list[Post],
    items: list[ContentItem],
    campaigns: list[Campaign],
    strict: bool = False,
) -> JoinResult:
    result = JoinResult(posts=list(content))

    # 1. ZoomSphere → kreatív, permalink, poszttípus, poszt-ID alapján
    by_id: dict[tuple[str, str], ContentItem] = {}
    for item in items:
        for channel, post_id in item.post_ids.items():
            if post_id:
                by_id[(channel, post_id)] = item

    for post in result.posts:
        item = by_id.get((post.channel, post.post_id))
        if item is None:
            result.unmatched_content.append(post)
            continue
        post.creatives = item.creatives.get(post.channel, [])
        post.post_type = post.post_type or item.post_type
        post.permalink = post.permalink or item.permalinks.get(post.channel, "")

    # 2. Meta Ads boostok → caption-prefix alapján
    for campaign in campaigns:
        if not campaign.is_boost:
            continue
        key = normalize_caption(campaign.name)[:MATCH_LENGTH]
        if not key:
            result.unmatched_boosts.append(campaign)
            continue
        match = next(
            (
                post
                for post in result.posts
                if post.channel == campaign.channel
                and post.paid is None
                and key in normalize_caption(post.caption)
            ),
            None,
        )
        if match is None:
            result.unmatched_boosts.append(campaign)
        else:
            match.paid = campaign

    if strict and result.unmatched_boosts:
        names = ", ".join(c.name for c in result.unmatched_boosts)
        raise UnmatchedBoostError(
            f"nem illeszthető boostolt poszt: {names}. "
            "Ellenőrizd, hogy a Tartalom export ugyanarra a hónapra és csatornára szól-e."
        )

    return result
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_join.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/join.py tests/test_join.py
git commit -m "feat: poszt-ID es caption alapu join a harom forras kozott"
```

---

## Task 12: KPI-számítás

**Files:**
- Create: `pipeline/kpi.py`
- Test: `tests/test_kpi.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_kpi.py`:

```python
import pytest

from pipeline.errors import ReachSummationError
from pipeline.kpi import content_summary, cross_channel, page_totals, paid_totals
from pipeline.parsers import meta_ads, meta_content, meta_daily, zoomsphere
from pipeline.join import join_posts
from pipeline.schema import DailySeries


@pytest.fixture
def posts(input_file):
    return join_posts(
        content=meta_content.parse(input_file("Jul-01-2026")).payload,
        items=zoomsphere.parse(input_file("Scheduler")).payload,
        campaigns=meta_ads.parse(input_file("Kampányok")).payload.campaigns,
    ).posts


def test_cross_channel_averages(posts):
    result = cross_channel(posts)
    assert result["avg_reach_organic_post"] == 130
    assert result["avg_reach_boosted_post"] == 4312
    assert result["boosted_share_of_post_reach"] == 0.917
    assert result["reach_multiplier"] == 33.2


def test_content_summary(input_file):
    items = zoomsphere.parse(input_file("Scheduler")).payload
    summary = content_summary(items)
    assert summary["total"] == 29
    assert summary["by_type"] == {"image": 14, "story": 14, "reel": 1}
    assert summary["stories_by_channel"] == {"facebook": 7, "instagram": 7}


def test_paid_totals_group_by_result_type(input_file):
    campaigns = meta_ads.parse(input_file("Kampányok")).payload.campaigns
    totals = paid_totals(campaigns)
    assert round(totals["spend"], 2) == 472.71
    assert totals["currency"] == "EUR"
    assert round(totals["always_on"]["spend"], 2) == 362.24
    assert round(totals["boosted"]["spend"], 2) == 110.47
    assert "actions:omni_landing_page_view" in totals["by_result_type"]


def test_page_totals_sum_additive_series(input_file):
    series = [meta_daily.parse(input_file(name)).payload for name in
              ("Felkeresések.csv", "Hivatkozáskattintások.csv", "Interakciók.csv")]
    totals = page_totals(series)
    assert totals["facebook"]["visits"] == 1525
    assert totals["facebook"]["link_clicks"] == 1227
    assert totals["facebook"]["interactions"] == 345


def test_page_totals_refuse_to_sum_reach():
    bad = DailySeries(channel="facebook", field="reach", metric="Elérés",
                      points=[(__import__("datetime").date(2026, 7, 1), 100)])
    with pytest.raises(ReachSummationError):
        page_totals([bad])
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_kpi.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.kpi'`

- [ ] **Step 3: Írd meg a modult**

`pipeline/kpi.py`:

```python
from collections import Counter, defaultdict

from pipeline.guards import sum_additive, sum_results
from pipeline.schema import Campaign, ContentItem, DailySeries, Post


def content_summary(items: list[ContentItem]) -> dict:
    stories = Counter()
    for item in items:
        if item.post_type == "story":
            for channel in item.post_ids:
                stories[channel] += 1
    return {
        "total": len(items),
        "by_type": dict(Counter(item.post_type for item in items)),
        "stories_by_channel": dict(stories),
    }


def page_totals(series: list[DailySeries]) -> dict:
    totals: dict[str, dict[str, float]] = defaultdict(dict)
    for entry in series:
        totals[entry.channel][entry.field] = sum_additive(
            [value for _, value in entry.points], field=entry.field
        )
    return {channel: dict(fields) for channel, fields in totals.items()}


def paid_totals(campaigns: list[Campaign]) -> dict:
    always_on = [c for c in campaigns if not c.is_boost]
    boosted = [c for c in campaigns if c.is_boost]

    by_type: dict[str, dict] = {}
    grouped: dict[str, list[Campaign]] = defaultdict(list)
    for campaign in campaigns:
        if campaign.result_type:
            grouped[campaign.result_type].append(campaign)
    for result_type, group in grouped.items():
        by_type[result_type] = {
            "campaigns": len(group),
            "spend": sum(c.spend for c in group),
            "results": sum_results(group),
        }

    def block(group: list[Campaign]) -> dict:
        return {
            "campaigns": len(group),
            "spend": sum(c.spend for c in group),
            "impressions": sum(c.impressions for c in group),
            "link_clicks": sum(c.link_clicks for c in group),
        }

    return {
        "spend": sum(c.spend for c in campaigns),
        "currency": campaigns[0].currency if campaigns else "EUR",
        "always_on": block(always_on),
        "boosted": block(boosted),
        "by_result_type": by_type,
    }


def cross_channel(posts: list[Post]) -> dict:
    """A riport csúcspontja: mennyit ér a boost.

    A poszt-elérések összege szándékosan NEM havi reach — csak arányszámításra
    használjuk, és a riport is így címkézi.
    """
    boosted = [p for p in posts if p.is_boosted]
    organic = [p for p in posts if not p.is_boosted]

    boosted_reach = sum(p.reach for p in boosted)
    organic_reach = sum(p.reach for p in organic)
    total_reach = boosted_reach + organic_reach

    avg_organic = round(organic_reach / len(organic)) if organic else 0
    avg_boosted = round(boosted_reach / len(boosted)) if boosted else 0

    return {
        "posts_total": len(posts),
        "posts_boosted": len(boosted),
        "posts_organic": len(organic),
        "post_reach_sum": total_reach,
        "avg_reach_organic_post": avg_organic,
        "avg_reach_boosted_post": avg_boosted,
        "boosted_share_of_post_reach": (
            round(boosted_reach / total_reach, 3) if total_reach else 0.0
        ),
        "reach_multiplier": round(avg_boosted / avg_organic, 1) if avg_organic else 0.0,
        "boost_spend": sum(p.paid.spend for p in boosted),
    }
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_kpi.py -q`
Expected: `5 passed`

Ha az `always_on` / `boosted` költés-bontás nem stimmel, a várt értékek: always-on = 66,53 + 152,16 + 57,70 + 64,99 + 20,86 = **362,24**, boosted = 13,90 + 13,82 + 13,90 + 13,91 + 13,95 + 15,99 + 15,95 + 9,05 = **110,47**. Összesen 472,71.

- [ ] **Step 5: Commit**

```bash
git add pipeline/kpi.py tests/test_kpi.py
git commit -m "feat: KPI-szamitas organic/paid keresztmetszettel"
```

---

## Task 13: Build — a teljes pipeline összekötése

**Files:**
- Create: `pipeline/build.py`
- Test: `tests/test_build.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_build.py`:

```python
import pytest

from pipeline.build import build
from pipeline.errors import ClientMismatchError, PeriodMismatchError


def test_build_produces_report_data(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    assert data["meta"]["client"] == "Larus Étterem"
    assert data["meta"]["period"] == "2026-07"
    assert data["meta"]["currency"] == "EUR"


def test_build_includes_every_section(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    for key in ("content", "posts", "page", "paid", "cross"):
        assert key in data, key


def test_build_reports_join_quality(fixture_dir):
    data = build(fixture_dir, period="2026-07")
    quality = data["quality"]
    assert quality["posts_with_creative"] == 15
    assert quality["dropped_zero_campaign_rows"] == 16
    # nincs IG Tartalom export a fixture-ben → a 4 IG boost jelentve, nem tippelve
    assert len(quality["unmatched_boosts"]) == 4


def test_wrong_period_is_rejected(fixture_dir):
    with pytest.raises(PeriodMismatchError):
        build(fixture_dir, period="2026-06")


def test_foreign_client_is_rejected(fixture_dir, tmp_path):
    import shutil, yaml

    other = tmp_path / "mammut-2026-07"
    shutil.copytree(fixture_dir, other)
    config = yaml.safe_load((other / "client.yaml").read_text(encoding="utf-8"))
    config["client"]["fb_page_id"] = "999999"
    (other / "client.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(ClientMismatchError):
        build(other, period="2026-07")
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_build.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.build'`

- [ ] **Step 3: Írd meg a modult**

`pipeline/build.py`:

```python
from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path

import yaml

from pipeline import guards, kpi
from pipeline.detect import scan
from pipeline.errors import UnknownSourceError
from pipeline.join import join_posts
from pipeline.parsers import meta_ads, meta_content, meta_daily, zoomsphere


def _serialise(value):
    if is_dataclass(value):
        return {key: _serialise(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialise(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def load_config(directory: Path) -> dict:
    path = Path(directory) / "client.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build(directory: Path, period: str) -> dict:
    directory = Path(directory)
    config = load_config(directory)
    client = config["client"]
    overrides = config.get("daily_metric_overrides") or {}
    overrides = {key: tuple(value) for key, value in overrides.items()}

    items, content, campaigns, series = [], [], [], []
    ads_payload = None
    hints: dict[str, str] = {}
    unknown: list[str] = []

    for source in scan(directory / "input"):
        if source.kind == "zoomsphere":
            parsed = zoomsphere.parse(source.path)
            items = parsed.payload
        elif source.kind == "meta_ads":
            parsed = meta_ads.parse(source.path)
            ads_payload = parsed.payload
            campaigns = parsed.payload.campaigns
        elif source.kind == "meta_content":
            parsed = meta_content.parse(source.path)
            content += parsed.payload
        elif source.kind == "meta_daily":
            parsed = meta_daily.parse(source.path, overrides=overrides)
            series.append(parsed.payload)
        else:
            unknown.append(source.path.name)
            continue

        guards.check_period(source.kind, parsed.period, period)
        hints.update({k: v for k, v in parsed.client_hints.items() if v})

    if unknown:
        raise UnknownSourceError("nem azonosítható fájl: " + ", ".join(unknown))

    guards.check_client(hints, client)

    joined = join_posts(content=content, items=items, campaigns=campaigns)

    return _serialise(
        {
            "meta": {
                "client": client["name"],
                "period": period,
                "currency": ads_payload.currency if ads_payload else "EUR",
                "language": config.get("report", {}).get("language", "hu"),
            },
            "content": kpi.content_summary(items),
            "posts": joined.posts,
            "page": kpi.page_totals(series),
            "paid": kpi.paid_totals(campaigns),
            "cross": kpi.cross_channel(joined.posts),
            "quality": {
                "posts_with_creative": sum(1 for p in joined.posts if p.creatives),
                "posts_total": len(joined.posts),
                "unmatched_boosts": [c.name for c in joined.unmatched_boosts],
                "unmatched_content": [p.post_id for p in joined.unmatched_content],
                "dropped_zero_campaign_rows": (
                    ads_payload.dropped_zero_rows if ads_payload else 0
                ),
            },
        }
    )
```

- [ ] **Step 4: Futtasd**

Run: `pytest tests/test_build.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add pipeline/build.py tests/test_build.py
git commit -m "feat: teljes pipeline osszekotese report_data-va"
```

---

## Task 14: CLI és golden file

**Files:**
- Create: `pipeline/cli.py`
- Create: `tests/fixtures/larus-2026-07/report_data.golden.json`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Írd meg a failing tesztet**

`tests/test_cli.py`:

```python
import json
from pathlib import Path

from pipeline.cli import main


def test_validate_prints_data_map(fixture_dir, capsys):
    exit_code = main([str(fixture_dir), "--period", "2026-07", "--validate"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "ZoomSphere" in out
    assert "29 tartalom" in out
    assert "15/16" in out
    assert "472.71 EUR" in out
    assert "nem illesztett boost" in out


def test_build_writes_report_data(fixture_dir, tmp_path):
    target = tmp_path / "report_data.json"
    exit_code = main(
        [str(fixture_dir), "--period", "2026-07", "--out", str(target)]
    )
    assert exit_code == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["cross"]["reach_multiplier"] == 33.2


def test_output_matches_the_golden_file(fixture_dir, tmp_path):
    target = tmp_path / "report_data.json"
    main([str(fixture_dir), "--period", "2026-07", "--out", str(target)])
    produced = json.loads(target.read_text(encoding="utf-8"))
    golden = json.loads(
        (Path(fixture_dir) / "report_data.golden.json").read_text(encoding="utf-8")
    )
    assert produced == golden
```

- [ ] **Step 2: Futtasd, hogy elbukjon**

Run: `pytest tests/test_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.cli'`

- [ ] **Step 3: Írd meg a CLI-t**

`pipeline/cli.py`:

```python
import argparse
import json
import sys
from pathlib import Path

from pipeline.build import build
from pipeline.errors import PipelineError


def _report_map(data: dict) -> str:
    quality = data["quality"]
    paid = data["paid"]
    content = data["content"]
    cross = data["cross"]
    channels = ", ".join(sorted(data["page"])) or "nincs"

    return "\n".join(
        [
            f"Ügyfél:   {data['meta']['client']}",
            f"Időszak:  {data['meta']['period']}",
            "",
            f"ZoomSphere      {content['total']} tartalom — " + ", ".join(
                f"{count} {name}" for name, count in content["by_type"].items()
            ),
            f"Tartalom        {quality['posts_total']} poszt, "
            f"kreatívval párosítva {quality['posts_with_creative']}/"
            f"{quality['posts_total']}",
            f"Meta Ads        {paid['always_on']['campaigns']} always-on + "
            f"{paid['boosted']['campaigns']} boost, "
            f"{paid['spend']:.2f} {paid['currency']} "
            f"({quality['dropped_zero_campaign_rows']} nullás sor kiszűrve)",
            f"Napi metrikák   {channels}",
            "",
            f"Organic poszt átlagos elérése:  {cross['avg_reach_organic_post']}",
            f"Boostolt poszt átlagos elérése: {cross['avg_reach_boosted_post']}"
            f"  ({cross['reach_multiplier']}×)",
            "",
            "⚠ nem illesztett boost: "
            + (", ".join(quality["unmatched_boosts"]) or "nincs"),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hello-report")
    parser.add_argument("directory", help="ügyfél-hónap mappa, pl. clients/larus/2026-07")
    parser.add_argument("--period", required=True, help="YYYY-MM")
    parser.add_argument("--validate", action="store_true", help="csak ellenőrzés")
    parser.add_argument("--out", default=None, help="report_data.json útvonala")
    args = parser.parse_args(argv)

    try:
        data = build(Path(args.directory), period=args.period)
    except PipelineError as error:
        print(f"HIBA: {error}", file=sys.stderr)
        return 1

    print(_report_map(data))

    if not args.validate:
        target = Path(args.out or Path(args.directory) / "report_data.json")
        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n→ {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Hozd létre a golden file-t**

```bash
python -m pipeline.cli tests/fixtures/larus-2026-07 --period 2026-07 \
  --out tests/fixtures/larus-2026-07/report_data.golden.json
```

Nézd át a kiírt adat-térképet, és **ellenőrizd**, hogy ezeket az értékeket tartalmazza:

```
ZoomSphere      29 tartalom — 14 image, 14 story, 1 reel
Tartalom        16 poszt, kreatívval párosítva 15/16
Meta Ads        5 always-on + 8 boost, 472.71 EUR (16 nullás sor kiszűrve)
Organic poszt átlagos elérése:  130
Boostolt poszt átlagos elérése: 4312  (33.2×)
⚠ nem illesztett boost: 4 db Instagram-bejegyzés
```

A 4 nem illesztett boost **helyes viselkedés**, nem hiba: a fixture-ben nincs IG
Tartalom export, tehát nincs mihez kötni őket. Amint az IG export bekerül, ez nullára megy.

Ha bármi más eltér, a hiba a pipeline-ban van — **ne írd felül a golden file-t, javítsd a kódot.**

- [ ] **Step 5: Futtasd az egész tesztkészletet**

Run: `pytest -q`
Expected: `78 passed`

Bontásban: smoke 2, textio 6, detect 4, schema 3, zoomsphere 6, meta_ads 7,
meta_content 6, meta_daily 13, guards 8, join 7, kpi 5, build 6, cli 5.

- [ ] **Step 6: Commit**

```bash
git add pipeline/cli.py tests/test_cli.py tests/fixtures/larus-2026-07/report_data.golden.json
git commit -m "feat: CLI --validate adat-terkeppel es golden file"
```

---

## Task 15: A spec frissítése a mért eredményekkel

**Files:**
- Modify: `docs/superpowers/specs/2026-08-05-hello-reporting-design.md`

- [ ] **Step 1: Írd át a 15. szekció (Nyitott kérdések) 3. sorát**

Ha a Task 8 során kiderült, hogy az IG Tartalom export oszlopai eltérnek a FB-étől,
a `meta_content.py`-ba került az eltérés kezelése. Frissítsd a nyitott kérdés státuszát
`eldőlt`-re, és írd le, mit találtál. Ha még nincs IG export, hagyd nyitva.

- [ ] **Step 2: Vezesd át a függőségváltozást**

A 4.3 szakaszban a `pandas` már nem szerepel. Ellenőrizd, hogy a `pyproject.toml`
és a spec ugyanazt a listát tartalmazza: `openpyxl`, `pyyaml`, `jinja2`, `pillow`, `requests`.

- [ ] **Step 3: Írd be a mért join-arányokat a 6. szekcióba**

A 6. szekció táblája már tartalmazza a 15/16, 4/4, 8/8 értékeket. Ha a Task 11
tesztjei más eredményt adtak, **a specet igazítsd a méréshez**, ne fordítva.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-08-05-hello-reporting-design.md
git commit -m "docs: spec szinkronizalasa az implementalt pipeline-nal"
```

---

## Mit ad ez a terv a végén

```
$ python -m pipeline.cli clients/larus/2026-07 --period 2026-07 --validate

Ügyfél:   Larus Étterem
Időszak:  2026-07

ZoomSphere      29 tartalom — 14 image, 14 story, 1 reel
Tartalom        16 poszt, kreatívval párosítva 15/16
Meta Ads        5 always-on + 8 boost, 472.71 EUR (16 nullás sor kiszűrve)
Napi metrikák   facebook, instagram

Organic poszt átlagos elérése:  130
Boostolt poszt átlagos elérése: 4312  (33.2×)

⚠ nem illesztett boost: Instagram-bejegyzés: Ennyi! 😉🥂 …  (4 db — hiányzik az IG Tartalom export)
```

Ezen a ponton a `report_data.json` teljes, ellenőrzött, és a 2. terv (renderelés)
már csak ebből dolgozik — forrásfájlt nem lát.

---

## Következő tervek

**2. terv — Renderelés:** `brand.css` a mért design tokenekkel, `charts.py` inline SVG-vel,
`report.html.j2` 16:9 oldalakkal, képletöltés és base64-beágyazás, `print.css`, PDF-gomb.

**3. terv — Narratíva, varázsló, review-kör:** `SKILL.md` és a `references/` dokumentumok,
export-varázsló a hiányzó fájlokra, `narrative.json` séma és szám-ellenőrzés,
`review.js` szerkesztéssel és megjegyzésekkel, `--apply-review`.
