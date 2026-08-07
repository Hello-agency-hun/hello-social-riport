"""A checklist — a Mammut-próba legdrágább hibájának javítása.

Nem kódhiba volt, hanem a kérés pontatlansága: a menedzser prózát kapott arról,
mit töltsön le, és ebből öt kör oda-vissza lett.
"""

from pipeline import checklist
from pipeline.cli import main


def test_it_works_without_any_configuration():
    """Ez a folyamat legelső lépése: még nincs client.yaml, se forrásfájl."""
    text = checklist.render(None, "clients/uj/2026-08")

    assert "clients/uj/2026-08/input/" in text
    assert "FACEBOOK" in text and "INSTAGRAM" in text, "fiók híján mindkettőt kérjük"


def test_a_facebook_only_client_is_not_asked_for_instagram():
    text = checklist.render({"fb_page_id": "1"}, "clients/x/2026-08")

    assert "Facebook" in text
    assert "INSTAGRAM" not in text
    assert "Instagram követőszám" not in text


def test_it_names_the_two_traps_that_cost_rounds():
    """A ZoomSphere PDF-ként és az Ads XLSX-ként érkezett — mindkettő egy-egy
    kört jelentett."""
    text = checklist.render(None, "clients/x/2026-08")

    assert "NEM pdf" in text, "ZoomSphere"
    assert "NEM xlsx" in text, "Meta Ads"


def test_it_names_what_must_not_be_uploaded():
    """A napi elérés-CSV hibával állította meg a buildet, és a ZoomSphere
    PDF-jével elment egy kör az átalakítási kísérletre."""
    text = checklist.render(None, "clients/x/2026-08")

    assert "NEM kell" in text
    assert "nem összegezhető" in text
    assert "poszt-azonosító" in text


def test_the_reach_tile_is_named_per_channel():
    """A Facebookon „Nézők", Instagramon „Elérés" — ez a két dolog, amiről a
    menedzser nem is sejti, hogy létezik."""
    text = checklist.render(None, "clients/x/2026-08")

    assert '"Nézők"' in text
    assert '"Elérés"' in text


def test_the_cli_flag_needs_no_sources(tmp_path, capsys):
    exit_code = main([str(tmp_path), "--period", "2026-08", "--checklist"])

    assert exit_code == 0
    assert "ZoomSphere" in capsys.readouterr().out
