from pipeline.errors import MissingColumnError
from pipeline.schema import ParsedSource, Post
from pipeline.tabular import read_table_rows
from pipeline.values import number, export_day
from pipeline.post_details import import_details

REQUIRED = ["Bejegyzésazonosító", "Elérés", "Megtekintések", "Állandó hivatkozás"]


def _channel(permalink: str) -> str:
    if "instagram.com" in permalink:
        return "instagram"
    return "facebook"


def parse(path) -> ParsedSource:
    rows = read_table_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Tartalom export")

    for column in REQUIRED:
        if column not in rows[0]:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")

    posts: list[Post] = []
    hints: dict[str, str] = {}

    for index, row in enumerate(rows, 2):
        def numeric(column):
            return number(row.get(column, ""), integer=True, label=f"{path.name}, {index}. sor, {column}")
        permalink = row.get("Állandó hivatkozás", "").strip()
        published = export_day(row.get("Közzététel időpontja"), label=f"{path.name}, {index}. sor: Közzététel időpontja")
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
                reach=numeric("Elérés"),
                views=numeric("Megtekintések"),
                # A Facebook exportjában `Reakciók`, az Instagraméban
                # `Kedvelések` — utóbbiban `Reakciók` oszlop nincs is. Amíg
                # csak az elsőt olvastuk, minden Instagram-poszt nulla
                # reakcióval jött be, a rezonanciája nullára esett, és a
                # riportban a mezőny mediánja is nulla lett.
                reactions=numeric("Reakciók" if row.get("Reakciók") else "Kedvelések"),
                comments=numeric("Hozzászólások"),
                shares=numeric("Megosztások"),
                # `Mentések` csak az Instagram exportjában van. Ha az oszlop
                # hiányzik, nem nullát írunk, hanem semmit.
                saves=numeric("Mentések") if "Mentések" in row else None,
                clicks=numeric("Összes kattintás"),
                link_clicks=numeric("Hivatkozáskattintások"),
                organic_measured=True,
                details=import_details(row, f'{path.name}, {index}. sor'),
            )
        )

    dates = sorted(post.published for post in posts)
    return ParsedSource(
        kind="meta_content",
        period=(dates[0], dates[-1]),
        client_hints=hints,
        payload=posts,
    )
