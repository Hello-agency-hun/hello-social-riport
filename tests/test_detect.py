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


def test_malformed_duplicate_is_ignored_when_valid_export_exists(tmp_path):
    valid = tmp_path / "Hello-Event-Kampányok-2026.-júl.-1.-2026.-júl.-31. -1.csv"
    valid.write_text(
        "Kampány neve,Elköltött összeg (HUF),Eredmény jelzése,Elérés,Megjelenések\n"
        "Teszt,1000,Elérés,10,20\n",
        encoding="utf-8",
    )
    malformed = tmp_path / "Hello-Event-Kampányok-2026.-júl.-1.-2026.-júl.-31.csv"
    malformed.write_text("hibás,fejléc\n1,2\n", encoding="utf-8")

    sources = {item.path.name: item.kind for item in scan(tmp_path)}

    assert sources[valid.name] == "meta_ads"
    assert sources[malformed.name] == "ignored_duplicate"


def test_unrelated_unknown_file_remains_unknown(tmp_path):
    unknown = tmp_path / "jegyzet.csv"
    unknown.write_text("foo,bar\na,b\n", encoding="utf-8")

    assert scan(tmp_path)[0].kind == "unknown"


def test_badly_named_content_export_is_recognized_from_its_data_pattern(tmp_path):
    path = tmp_path / "letoltes-vegleges.dat"
    path.write_text(
        "Bejegyzésazonosító,Elérés,Megtekintések,Állandó hivatkozás,Közzététel időpontja\n"
        "123,10,20,https://facebook.com/123,07/01/2026 10:00\n",
        encoding="utf-8",
    )

    assert identify(path).kind == "meta_content"


def test_header_only_export_is_still_recognized_before_empty_file_validation(tmp_path):
    path = tmp_path / "ures-export.akarmi"
    path.write_text(",".join([
        "Kampány neve", "Eredmény jelzése", "Elérés", "Megjelenések"
    ]) + "\n", encoding="utf-8")

    assert identify(path).kind == "meta_ads"


def test_probable_ads_export_is_classified_even_when_one_required_header_is_broken(tmp_path):
    """A parser mondja meg a konkrét hiányt; ne vesszen el az ismeretlen kategóriában."""
    path = tmp_path / "teljesen-ismeretlen-nev.csv"
    path.write_text(
        "elrontott első oszlop,Eredmény jelzése,Elérés,Megjelenések,Jelentés kezdete,Jelentés vége\n"
        "Teszt,reach,10,20,2026-07-01,2026-07-31\n",
        encoding="utf-8",
    )

    assert identify(path).kind == "meta_ads"
