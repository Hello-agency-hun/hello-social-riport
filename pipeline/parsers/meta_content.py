from datetime import datetime

from pipeline.errors import MissingColumnError
from pipeline.schema import ParsedSource, Post
from pipeline.textio import read_csv_rows

REQUIRED = ["Bejegyzésazonosító", "Elérés", "Megtekintések", "Állandó hivatkozás"]


def _number(value: str) -> int:
    value = (value or "").strip()
    try:
        return int(float(value))
    except ValueError:
        return 0


def _channel(permalink: str) -> str:
    if "instagram.com" in permalink:
        return "instagram"
    return "facebook"


def parse(path) -> ParsedSource:
    rows = read_csv_rows(path)
    if not rows:
        raise MissingColumnError(f"{path}: üres Tartalom export")

    for column in REQUIRED:
        if column not in rows[0]:
            raise MissingColumnError(f"{path}: hiányzó oszlop — {column}")

    posts: list[Post] = []
    hints: dict[str, str] = {}

    for row in rows:
        permalink = row.get("Állandó hivatkozás", "").strip()
        published = datetime.strptime(
            row["Közzététel időpontja"].strip(), "%m/%d/%Y %H:%M"
        ).date()
        hints.setdefault("page_id", row.get("Oldalazonosító", "").strip())
        hints.setdefault("page_name", row.get("Oldal neve", "").strip())

        posts.append(
            Post(
                channel=_channel(permalink),
                post_id=row["Bejegyzésazonosító"].strip(),
                published=published,
                caption=row.get("Cím", "").strip(),
                permalink=permalink,
                post_type=row.get("Bejegyzés típusa", "").strip(),
                reach=_number(row.get("Elérés", "")),
                views=_number(row.get("Megtekintések", "")),
                reactions=_number(row.get("Reakciók", "")),
                comments=_number(row.get("Hozzászólások", "")),
                shares=_number(row.get("Megosztások", "")),
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
