"""SVG grafikonok, külső chart-könyvtár nélkül.

Miért nem matplotlib vagy JS: a riport nyomtatásra és offline megnyitásra készül.
Az SVG vektoros (a PDF-ben éles marad), nulla függőség, és a színei a brand.css
tokenjeiből jönnek — ha az akcentus változik, a grafikonok követik.
"""

from datetime import date

W, H = 620, 260
PAD_L, PAD_R, PAD_T, PAD_B = 8, 8, 18, 26

PEAK_COUNT = 3
# Két felcímkézett csúcs között legalább ennyi nap legyen. Nem csak azért, hogy
# ne ugyanannak a kiugrásnak a szomszédos napjait jelöljük meg háromszor, hanem
# mert közelebb a két címke egymásra csúszna.
MIN_PEAK_GAP = 5

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
    return f"{int(value):,}".replace(",", " ")


def _percent(share: float) -> str:
    """Magyar tizedesjel. A riport szövege is vesszőt használ — egy oldalon
    belül nem lehet kétféle jelölés.

    (A riport v1-ben magyar nyelvű; ha később angol változat is lesz, ez a
    formázás nyelvfüggő paraméterré válik.)
    """
    return f"{share * 100:.1f}".replace(".", ",") + "%"


def line_chart(
    points: list[tuple[date, float]],
    label: str,
    height: int = H,
    colour: str = "var(--accent)",
) -> str:
    """Napi idősor. Egyetlen pontnál vízszintes vonalat rajzol, nem oszt nullával.

    A grafikon önmagában is leolvasható: vízszintes rácsvonalak értékkel, a
    csúcspont megjelölve és felcímkézve, a lábban az időszak összege. Egyetlen
    „max" felirat kevés ahhoz, hogy bárki bármit kezdjen a görbével.

    A `height` azért állítható, mert a trend-oldalon négy grafikon kerül egy
    16:9-es lapra — alapmagassággal az alsó sor lelógna az oldalról. A `colour`
    pedig azért, hogy egy oldalon a négy görbe ne legyen mind ugyanolyan zöld.
    """
    if not points:
        return _empty(label, W, height)

    values = [value for _, value in points]
    top = max(values) or 1
    span = max(len(points) - 1, 1)

    gutter = 52  # hely a rácsvonalak értékeinek
    inner_w = W - gutter - PAD_R - 8
    inner_h = height - PAD_T - PAD_B

    def at(index: int, value: float) -> tuple[float, float]:
        return (
            gutter + inner_w * index / span,
            PAD_T + inner_h * (1 - value / top),
        )

    coords = [at(index, value) for index, value in enumerate(values)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)

    parts = [_open(label, W, height)]

    # Rácsvonalak: nulla, fél, csúcs — így minden pont leolvasható.
    for share in (0.0, 0.5, 1.0):
        y = PAD_T + inner_h * (1 - share)
        parts.append(
            f'<line x1="{gutter}" y1="{y:.1f}" x2="{gutter + inner_w}" y2="{y:.1f}" '
            f'stroke="var(--rule)" stroke-width="1"'
            + ('' if share == 0 else ' stroke-dasharray="2 4"')
            + "/>"
            f'<text x="{gutter - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="var(--ink-soft)">{_thousands(top * share)}</text>'
        )

    area = (
        f"M{gutter},{PAD_T + inner_h} L" + " L".join(
            f"{x:.1f},{y:.1f}" for x, y in coords
        ) + f" L{gutter + inner_w},{PAD_T + inner_h} Z"
    )
    parts.append(f'<path d="{area}" fill="{colour}" opacity=".12"/>')
    parts.append(
        f'<polyline points="{path}" fill="none" stroke="{colour}" '
        'stroke-width="2.5" stroke-linejoin="round"/>'
    )

    # A három legerősebb nap megjelölve. Minimum távolság kell közéjük,
    # különben ugyanannak a kiugrásnak a három szomszédos napját címkéznénk fel.
    peaks: list[int] = []
    for index in sorted(range(len(values)), key=lambda i: -values[i]):
        if values[index] <= 0:
            break
        if all(abs(index - chosen) >= MIN_PEAK_GAP for chosen in peaks):
            peaks.append(index)
        if len(peaks) == PEAK_COUNT:
            break

    for rank, index in enumerate(peaks):
        px, py = at(index, values[index])
        anchor = "start" if index < len(values) * 0.72 else "end"
        offset = 8 if anchor == "start" else -8
        strong = rank == 0
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{4 if strong else 3}" '
            f'fill="{colour}" stroke="var(--paper)" stroke-width="2"/>'
            f'<text x="{px + offset:.1f}" y="{py - 9:.1f}" text-anchor="{anchor}" '
            f'font-size="{13 if strong else 12}" '
            f'font-weight="{700 if strong else 500}" '
            f'fill="var(--ink{"" if strong else "-soft"})">'
            f"{_thousands(values[index])}</text>"
            f'<text x="{px + offset:.1f}" y="{py - 23:.1f}" text-anchor="{anchor}" '
            f'font-size="10" fill="var(--ink-soft)">'
            f'{_escape(points[index][0].strftime("%m.%d."))}</text>'
        )

    parts.append(
        f'<text x="{gutter}" y="{height - 6}" font-size="11" fill="var(--ink-soft)">'
        f'{_escape(points[0][0].strftime("%m.%d."))}</text>'
        f'<text x="{gutter + inner_w}" y="{height - 6}" text-anchor="end" '
        f'font-size="11" fill="var(--ink-soft)">'
        f'{_escape(points[-1][0].strftime("%m.%d."))}</text>'
        f'<text x="{gutter + inner_w / 2}" y="{height - 6}" text-anchor="middle" '
        f'font-size="11" fill="var(--ink-soft)">összesen {_thousands(sum(values))}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def bar_chart(
    items: list[tuple[str, float]], label: str, colour: str = "var(--brand-rose)"
) -> str:
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
            f'rx="7" fill="{colour}"/>'
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
            f"{_escape(name)} — {_percent(share)}</text>"
        )
        offset += length

    return "".join(
        [_open(label, 300, 300 + 22 * len(parts))] + segments + legend + ["</svg>"]
    )
