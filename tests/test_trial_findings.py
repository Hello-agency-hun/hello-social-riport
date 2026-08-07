"""Amit a Mammut-próba hozott ki — mind valós adaton derült ki.

Ezek a hibák a Larus-fixture-ön sosem jelentek volna meg: az az egy ügyfél
egyféleképpen nevezi a kampányait, egyféle csempekészletet tölt le, és nincs
Instagram Tartalom exportja.
"""

import shutil

import pytest

from pipeline import performance
from pipeline.build import build
from pipeline.detect import DAILY_METRICS, identify
from pipeline.errors import DailyReachNotUsable, UnmatchedBoostError, WrongFormatError
from pipeline.parsers import meta_daily
from pipeline.render import _period_range


def _daily(path, metric, rows=3):
    path.write_text(
        'sep=,\n"' + metric + '"\n"Dátum","Primary"\n'
        + "".join(f'"2026-07-0{i + 1}T00:00:00","{i * 10}"\n' for i in range(rows)),
        encoding="utf-8",
    )
    return path


def test_instagram_follows_is_a_known_tile():
    """A README azt állította, hogy Instagramon nincs napi követés-csempe.
    A Mammutnál van, kétszáznyolcvankilenc új követéssel. A tévedés miatt a
    követőszám-lánc Instagramon sosem indult el."""
    assert DAILY_METRICS["Instagram-követések"] == ("instagram", "follows")


def test_a_daily_reach_tile_is_refused_gently(tmp_path):
    """Logikus, hogy a menedzser letölti — a havi eléréshez pont ezt a csempét
    kell megnyitni. Forrásként viszont használhatatlan. Eddig hibával állt meg
    rajta, és öt olyan mezőnevet kínált, amiből egyik sem jó."""
    source = _daily(tmp_path / "Nezok.csv", "Nézők")

    with pytest.raises(DailyReachNotUsable) as caught:
        meta_daily.parse(source)

    message = str(caught.value)
    assert "nincs szükség" in message
    assert "nem összegezhető" in message, "mondjuk meg, miért"
    assert "monthly_reach" in message, "és azt is, hova kerüljön helyette"


def test_a_foreign_xlsx_is_convertible_not_unknown(tmp_path):
    """A Mammutnál az Ads-export XLSX-ként jött. „Ismeretlen fájl" itt
    haszontalan válasz: a tartalma jó, csak CSV-vé kell menteni."""
    import zipfile

    path = tmp_path / "kampanyok.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")

    assert identify(path).kind == "spreadsheet"


def test_a_foreign_xlsx_gets_an_actionable_message(fixture_dir, tmp_path):
    import zipfile

    work = tmp_path / "xlsx"
    shutil.copytree(fixture_dir, work)
    with zipfile.ZipFile(work / "input" / "ads.xlsx", "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")

    with pytest.raises(WrongFormatError) as caught:
        build(work, period="2026-07")

    assert "CSV-ként" in str(caught.value)


def test_the_zoomsphere_pdf_is_declared_hopeless(fixture_dir, tmp_path):
    """Az `AGENTS.md` szerint „előbb próbáld meg" — de a ZoomSphere PDF-je
    elvileg sem elég: nincs benne poszt-azonosító és kép-URL. Egy fölösleges
    kör spórolható azzal, ha ezt kimondjuk."""
    work = tmp_path / "zs-pdf"
    shutil.copytree(fixture_dir, work)
    (work / "input" / "export.pdf").write_bytes(b"%PDF-1.7\n" + b"\x00" * 32)

    with pytest.raises(WrongFormatError) as caught:
        build(work, period="2026-07")

    assert "elvileg sem elég" in str(caught.value)


def test_mass_unmatched_boosts_stop_the_build():
    """A Mammut-próbán MINDEN boost illesztetlen maradt egy elrontott
    előtag-regex miatt, és a build ettől még „sikeresen" lefutott. A javítás
    után a boost-szorzó 2,5×-ről 4,7×-re változott — mindkét szám hihető volt,
    az egyik hamis."""
    from types import SimpleNamespace

    from pipeline.build import _check_boost_matching

    boosts = [SimpleNamespace(name=f"Boost {i}", is_boost=True) for i in range(10)]
    joined = SimpleNamespace(unmatched_boosts=boosts)

    with pytest.raises(UnmatchedBoostError) as caught:
        _check_boost_matching(joined, boosts)

    message = str(caught.value)
    assert "100%" in message
    assert "hamis" in message, "mondjuk meg, mi romlana el"


def test_a_few_unmatched_boosts_are_still_allowed():
    """Az előző hónapban megjelent, most hirdetett poszt normális eset."""
    from types import SimpleNamespace

    from pipeline.build import _check_boost_matching

    boosts = [SimpleNamespace(name=f"B{i}", is_boost=True) for i in range(10)]
    _check_boost_matching(SimpleNamespace(unmatched_boosts=boosts[:2]), boosts)


def test_the_report_declares_its_exact_period():
    """A korábbi kézi riportok metrikánként hét-tíz nappal korábban zárultak.
    Az ügyfél ugrást fog látni, és annak megmagyarázhatónak kell lennie."""
    assert _period_range("2026-07") == "2026-07-01 – 2026-07-31"
    assert _period_range("2026-02") == "2026-02-01 – 2026-02-28"
    assert _period_range("2028-02") == "2028-02-01 – 2028-02-29", "szökőév"


def test_the_period_is_visible_in_the_report(fixture_dir, tmp_path):
    import json

    from pipeline.render import render

    golden = fixture_dir / "report_data.golden.json"
    data = json.loads(golden.read_text(encoding="utf-8"))
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")

    assert "2026-07-01 – 2026-07-31" in html
