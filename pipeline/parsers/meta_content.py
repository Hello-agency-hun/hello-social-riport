from pipeline.errors import MissingColumnError
from pipeline.schema import ParsedSource, Post
from pipeline.tabular import parse_date, parse_number, read_table_rows

REQUIRED = ["Bejegyzésazonosító", "Elérés", "Megtekintések", "Állandó hivatkozás"]
PUBLISHED = "Közzététel időpontja"


def _number(value: str) -> int:
    """Üres cella nulla. Az ezres tagolású `1 234` viszont nem az: korábban
    az `int(float(…))` ezen elbukott, és a poszt elérése csendben nulla lett."""
    return int(parse_number(value) or 0)


def _channel(permalink: str) -> str:
    if "instagram.com" in permalink:
        return "instagram"
    return "facebook"


def parse(path) -> ParsedSource:
    rows = read_table_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Tartalom export")

    for column in (*REQUIRED, PUBLISHED):
        if column not in rows[0]:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")

    posts: list[Post] = []
    hints: dict[str, str] = {}

    for row in rows:
        permalink = row.get("Állandó hivatkozás", "").strip()
        # A Meta `07/04/2026 01:00` alakban adja; a magyar Excelben mentett
        # példány `2026. 07. 04. 1:00`-t. Korábban csak az elsőt ismertük, és
        # a másikon nyers `ValueError`-ral álltunk meg.
        published = parse_date(row[PUBLISHED])
        if published is None:
            raise MissingColumnError(
                f"{path}: értelmezhetetlen közzétételi időpont: {row[PUBLISHED]!r} "
                f"(poszt: {row.get('Bejegyzésazonosító', '').strip() or '?'}). "
                "Várt alak: 07/04/2026 01:00. Töltsd le újra a Business Suite-ból, "
                "megnyitás és mentés nélkül."
            )
        hints.setdefault("page_id", row.get("Oldalazonosító", "").strip())
        hints.setdefault("page_name", row.get("Oldal neve", "").strip())

        posts.append(
            Post(
                channel=_channel(permalink),
                post_id=row["Bejegyzésazonosító"].strip(),
                published=published,
                # A Facebook exportban a poszt szövege a „Cím", az Instagram
                # exportjában viszont nincs ilyen oszlop — ott a „Leírás". Amíg
                # csak a „Cím"-et néztük, minden Instagram-poszt szöveg nélkül
                # maradt, és mivel a boostokat szöveg alapján illesztjük, egy
                # instagramos hirdetett poszt sem kapta meg a költését.
                caption=(row.get("Cím") or row.get("Leírás") or "").strip(),
                permalink=permalink,
                post_type=row.get("Bejegyzés típusa", "").strip(),
                reach=_number(row.get("Elérés", "")),
                views=_number(row.get("Megtekintések", "")),
                # A Facebook exportjában `Reakciók`, az Instagraméban
                # `Kedvelések` — utóbbiban `Reakciók` oszlop nincs is. Amíg
                # csak az elsőt olvastuk, minden Instagram-poszt nulla
                # reakcióval jött be, a rezonanciája nullára esett, és a
                # riportban a mezőny mediánja is nulla lett.
                reactions=_number(row.get("Reakciók") or row.get("Kedvelések") or ""),
                comments=_number(row.get("Hozzászólások", "")),
                shares=_number(row.get("Megosztások", "")),
                # `Mentések` csak az Instagram exportjában van. Ha az oszlop
                # hiányzik, nem nullát írunk, hanem semmit.
                saves=_number(row["Mentések"]) if "Mentések" in row else None,
                clicks=_number(row.get("Összes kattintás", "")),
                link_clicks=_number(row.get("Hivatkozáskattintások", "")),
                organic_measured=True,
            )
        )

    dates = sorted(post.published for post in posts)
    return ParsedSource(
        kind="meta_content",
        period=(dates[0], dates[-1]),
        client_hints=hints,
        payload=posts,
    )
