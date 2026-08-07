"""A hiányzó kreatív pótlása a poszt Facebook-oldaláról.

A képek a ZoomSphere-ből jönnek, a számok a Metából. Ha egy poszt közvetlenül a
felületen ment ki, a teljesítménye megvan, a kreatívja nincs — és a riportban
helyőrző áll a helyén.

A Facebook viszont kiadja a poszt nyitóképét `og:image` metaadatként. Ez
**kiegészítés, nem forrás**: ha nem megy, marad a helyőrző.
"""

from pipeline import images

PAGE = (
    '<html><head><meta property="og:image" '
    'content="https://scontent.fbud3-2.fna.fbcdn.net/kep.jpg?a=1&amp;b=2">'
    "</head><body>…</body></html>"
).encode("utf-8")

PERMALINK = "https://www.facebook.com/larusetterem/posts/pfbid0rbkdek"


def test_the_opening_image_is_read_from_the_post_page():
    found, why = images.creative_from_permalink(PERMALINK, fetcher=lambda url: PAGE)
    assert found == "https://scontent.fbud3-2.fna.fbcdn.net/kep.jpg?a=1&b=2", (
        "a HTML-entitásokat vissza kell alakítani, különben az URL nem tölthető le"
    )
    assert why == "megvan"


def test_a_page_without_the_tag_says_why():
    """A Mammut-próbán mindhárom pótlás eredménytelen maradt, és nem derült ki,
    miért — így a menedzser nem tudta eldönteni, érdemes-e kézzel pótolni."""
    found, why = images.creative_from_permalink(PERMALINK, fetcher=lambda u: b"<html>")

    assert found is None
    assert "nincs og:image" in why


def test_a_failed_request_falls_back_quietly_but_audibly():
    """A hiányzó kép kellemetlen; egy elszálló build sokkal rosszabb."""

    def boom(url):
        raise OSError("nincs hálózat")

    found, why = images.creative_from_permalink(PERMALINK, fetcher=boom)
    assert found is None
    assert "nem érhető el" in why


def test_only_facebook_links_are_followed():
    """Az Instagram-permalinkek nem adnak `og:image`-et, és nem is akarunk
    tetszőleges URL-t lekérni azért, mert egy exportban szerepelt."""
    assert images.creative_from_permalink("https://example.com/x", lambda u: PAGE)[0] is None
    assert images.creative_from_permalink("", lambda u: PAGE)[0] is None


def test_an_offline_build_says_so_rather_than_staying_silent():
    found, why = images.creative_from_permalink(PERMALINK, fetcher=lambda u: b"")
    assert found is None
    assert "offline" in why


def test_offline_builds_do_not_reach_out(tmp_path):
    """A `--offline` üres bájtsort ad vissza minden URL-re. Ilyenkor a
    helyőrző marad, és nem indul hálózati kérés."""
    from pipeline.render import render

    import json
    from pathlib import Path

    golden = (
        Path(__file__).parent / "fixtures" / "larus-2026-07" / "report_data.golden.json"
    )
    data = json.loads(golden.read_text(encoding="utf-8"))
    html = render(data, cache_dir=tmp_path, fetcher=lambda url: b"")

    assert "kép nem elérhető" in html or "data:image/svg+xml" in html
