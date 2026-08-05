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


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _open(label: str, width: int = W, height: int = H) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{_escape(label)}" class="chart">'
    )


def _empty(label: str, width: int = W, height: int = H) -> str:
    return (
        _open(label, width, height)
        + f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" '
        'fill="none" stroke="var(--rule)"/>'
        f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" '
        'font-size="14" fill="var(--ink-soft)">nincs adat</text></svg>'
    )


def _thousands(value: float) -> str:
    return f"{int(value):,}".replace(",", " ")


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
        f"M{PAD_L},{PAD_T + inner_h} L" + " L".join(coords)
        + f" L{PAD_L + inner_w},{PAD_T + inner_h} Z"
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
            f"max {_thousands(top)}</text>",
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
            f'fill="var(--ink)">{_thousands(value)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def donut(parts: list[tuple[str, float]], label: str) -> str:
    """Gyűrűdiagram `stroke-dasharray`-jel — nincs szükség ív-matematikára."""
    total = sum(value for _, value in parts)
    if not parts or total <= 0:
        return _empty(label, 300, 300)

    radius = 60
    circumference = 2 * 3.141592653589793 * radius
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
