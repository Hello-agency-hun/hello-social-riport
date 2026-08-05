"""Open Sauce One vendorálása a repóba. Egyszer fut, az eredménye commitolva.

A font OFL licencű, tehát terjeszthető. A HELLO brand guide `Open Sauce Sans`-t
nevez meg, a benchmark riport viszont `Open Sauce One`-t használ — a riportban
az utóbbi az irányadó.
"""

import io
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.textio import force_utf8_output  # noqa: E402

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
    force_utf8_output()
    raise SystemExit(main())
