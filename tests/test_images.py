import io

import pytest
from PIL import Image

from pipeline.images import PLACEHOLDER, embed, to_data_uri


def _jpeg(width=1200, height=900, colour=(200, 40, 160)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_data_uri_is_a_jpeg():
    assert to_data_uri(_jpeg()).startswith("data:image/jpeg;base64,")


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
