"""A HELLO logó kinyerése a brand guide PDF-ből, vektorosan.

Egyszer fut, az eredménye (`assets/logo/*.svg`) commitolva. A brand guide tiltja
a logó nyújtását, átszínezését és átszabását — ezért nem újrarajzoljuk, hanem
az eredeti vektor-útvonalakat vesszük át bájthűen.

A guide 4. oldalán a logó fekete kitöltésű útvonal, a körülötte lévő szerkesztési
rács világosszürke vonal. A szűrés a kitöltés színe alapján történik, így a rács
nem kerül bele.

Használat:
    python tools/extract_logo.py "<brand guide pdf>"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.textio import force_utf8_output  # noqa: E402

TARGET = Path(__file__).resolve().parent.parent / "assets" / "logo"

PAGE = 3  # 0-alapú: "1.0 - Our logo"
BLACK = (0.0, 0.0, 0.0)

# A guide 4. oldalán mért befoglaló dobozok (1920×1080-as oldalon).
REGIONS = {
    "hello-mark": (655, 360, 925, 666),
    "hello-lockup": (1165, 360, 1710, 666),
}


def _path_data(items) -> str:
    """PyMuPDF rajz-elemekből SVG `d` attribútum.

    A szakaszok sorrendben követik egymást: ha egy elem ott kezdődik, ahol az
    előző véget ért, ugyanannak a részútvonalnak a folytatása. Új `M`-et csak
    valódi részútvonal-határon szabad írni — különben a kitöltés szétesik,
    és a logó helyén törmelék jelenik meg.
    """
    out: list[str] = []
    current: tuple[float, float] | None = None

    def at(point) -> tuple[float, float]:
        return (round(point.x, 2), round(point.y, 2))

    def close():
        nonlocal current
        if current is not None:
            out.append("Z")
            current = None

    for item in items:
        kind = item[0]

        if kind in ("l", "c"):
            start = item[1]
            end = item[2] if kind == "l" else item[4]
            if current != at(start):
                close()
                out.append(f"M{start.x:.2f} {start.y:.2f}")
            if kind == "l":
                out.append(f"L{end.x:.2f} {end.y:.2f}")
            else:
                c1, c2 = item[2], item[3]
                out.append(
                    f"C{c1.x:.2f} {c1.y:.2f} {c2.x:.2f} {c2.y:.2f}"
                    f" {end.x:.2f} {end.y:.2f}"
                )
            current = at(end)

        elif kind == "re":
            close()
            rect = item[1]
            out.append(
                f"M{rect.x0:.2f} {rect.y0:.2f}H{rect.x1:.2f}"
                f"V{rect.y1:.2f}H{rect.x0:.2f}Z"
            )

        elif kind == "qu":
            close()
            quad = item[1]
            points = [quad.ul, quad.ur, quad.lr, quad.ll]
            out.append(f"M{points[0].x:.2f} {points[0].y:.2f}")
            out += [f"L{p.x:.2f} {p.y:.2f}" for p in points[1:]]
            out.append("Z")

    close()
    return "".join(out)


def extract(pdf_path: Path) -> int:
    import pymupdf

    document = pymupdf.open(pdf_path)
    page = document[PAGE]
    drawings = [d for d in page.get_drawings() if d.get("fill") == BLACK]

    TARGET.mkdir(parents=True, exist_ok=True)

    for name, (x0, y0, x1, y1) in REGIONS.items():
        box = pymupdf.Rect(x0, y0, x1, y1)
        selected = [d for d in drawings if box.contains(d["rect"])]
        if not selected:
            print(f"{name}: nincs útvonal a régióban — a mért doboz elavult?")
            return 1

        bounds = selected[0]["rect"]
        for drawing in selected[1:]:
            bounds |= drawing["rect"]

        paths = []
        for drawing in selected:
            data = _path_data(drawing["items"])
            if not data:
                continue
            rule = "evenodd" if drawing.get("even_odd") else "nonzero"
            paths.append(f'<path d="{data}" fill-rule="{rule}"/>')

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{bounds.x0:.2f} {bounds.y0:.2f} '
            f'{bounds.width:.2f} {bounds.height:.2f}" '
            f'role="img" aria-label="HELLO Agency">'
            '<g fill="currentColor">' + "".join(paths) + "</g></svg>"
        )
        out = TARGET / f"{name}.svg"
        out.write_text(svg, encoding="utf-8")
        print(
            f"{out.name}: {len(selected)} útvonal, "
            f"{bounds.width:.0f}×{bounds.height:.0f}, {len(svg)} byte"
        )

    return 0


if __name__ == "__main__":
    force_utf8_output()
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(extract(Path(sys.argv[1])))
