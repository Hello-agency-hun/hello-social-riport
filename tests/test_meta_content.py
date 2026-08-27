from datetime import date

from pipeline.periods import filter_posts
from pipeline.parsers.meta_content import parse


def test_parses_all_posts(input_file):
    assert len(parse(input_file("Jul-01-2026")).payload) == 16


def test_channel_is_derived_from_the_permalink(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    assert {p.channel for p in posts} == {"facebook"}


def test_top_post_metrics(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    top = max(posts, key=lambda p: p.reach)
    assert top.caption.startswith("Séfünk ajánlata!")
    assert top.reach == 9046
    assert top.views == 11810
    assert top.link_clicks == 1027


def test_post_id_has_no_page_prefix(input_file):
    posts = parse(input_file("Jul-01-2026")).payload
    assert all("_" not in p.post_id for p in posts)


def test_client_hints_carry_page_identity(input_file):
    hints = parse(input_file("Jul-01-2026")).client_hints
    assert hints["page_id"] == "100064824963030"
    assert hints["page_name"] == "Larus Étterem"


def test_period_spans_july(input_file):
    assert parse(input_file("Jul-01-2026")).period == (
        date(2026, 7, 1),
        date(2026, 7, 31),
    )


def test_instagram_caption_comes_from_the_description_column(tmp_path):
    """Az Instagram Tartalom exportjában nincs „Cím" oszlop.

    A poszt szövege ott a „Leírás". Amíg csak a „Cím"-et olvastuk, minden
    Instagram-poszt szöveg nélkül maradt — és mivel a boostokat a szöveg
    alapján illesztjük, egyetlen instagramos hirdetett poszt sem kapta meg a
    költését. A riportban organikusként látszottak volna.
    """
    csv_path = tmp_path / "ig.csv"
    csv_path.write_text(
        "Bejegyzésazonosító,Fiókazonosító,Leírás,"
        '"Közzététel időpontja","Állandó hivatkozás","Bejegyzés típusa",'
        "Megtekintések,Elérés\n"
        "181,178,Hangolódj a nyári vízparti hangulatra,"
        '"07/03/2026 10:00","https://www.instagram.com/reel/AAA/",REEL,10,5\n',
        encoding="utf-8",
    )
    post = parse(csv_path).payload[0]
    assert post.channel == "instagram"
    assert post.caption == "Hangolódj a nyári vízparti hangulatra"


def test_facebook_title_still_wins_over_the_description(tmp_path):
    """A Facebook exportban mindkét oszlop létezik — a viselkedés nem változhat."""
    csv_path = tmp_path / "fb.csv"
    csv_path.write_text(
        'Bejegyzésazonosító,Oldalazonosító,"Oldal neve",Cím,Leírás,'
        '"Közzététel időpontja","Állandó hivatkozás","Bejegyzés típusa",'
        "Megtekintések,Elérés\n"
        '148,100,"Mammut","A poszt szövege","hosszabb leírás",'
        '"07/03/2026 10:00","https://www.facebook.com/100_148",POST,10,5\n',
        encoding="utf-8",
    )
    post = parse(csv_path).payload[0]
    assert post.caption == "A poszt szövege"


def test_content_filter_drops_posts_outside_the_requested_dates(input_file):
    posts = parse(input_file("Jul-01-2026")).payload

    filtered = filter_posts(posts, date(2026, 7, 10), date(2026, 7, 20))

    assert filtered
    assert all(date(2026, 7, 10) <= post.published <= date(2026, 7, 20)
               for post in filtered)


def test_instagram_likes_are_read_as_reactions(tmp_path):
    """Az Instagram Tartalom exportjában nincs `Reakciók` oszlop.

    Ott `Kedvelések` a neve. Amíg csak a `Reakciók`-at olvastuk, minden
    Instagram-poszt nulla reakcióval jött be: a Mammut júliusi exportjában
    tizenkilenc posztra nulla reakció, miközben hozzászólás és megosztás volt.
    Ettől a rezonancia nullára esett, a mezőny mediánja is nulla lett, és a
    riportban a `nincs stabil alap` felirat jelent meg.
    """
    csv_path = tmp_path / "ig.csv"
    csv_path.write_text(
        "Bejegyzésazonosító,Fiókazonosító,Leírás,"
        '"Közzététel időpontja","Állandó hivatkozás","Bejegyzés típusa",'
        "Megtekintések,Elérés,Kedvelések,Megosztások,Hozzászólások,Mentések\n"
        "181,178,Nyári ajánlat,"
        '"07/03/2026 10:00","https://www.instagram.com/reel/AAA/",REEL,100,80,42,3,5,7\n',
        encoding="utf-8",
    )
    post = parse(csv_path).payload[0]
    assert post.channel == "instagram"
    assert post.reactions == 42
    assert post.comments == 5
    assert post.shares == 3


def test_facebook_reactions_column_still_wins(tmp_path):
    csv_path = tmp_path / "fb.csv"
    csv_path.write_text(
        'Bejegyzésazonosító,Oldalazonosító,"Oldal neve",Cím,'
        '"Közzététel időpontja","Állandó hivatkozás","Bejegyzés típusa",'
        "Megtekintések,Elérés,Reakciók,Hozzászólások,Megosztások\n"
        '148,100,"Mammut","A poszt",'
        '"07/03/2026 10:00","https://www.facebook.com/100_148",POST,100,80,9,2,1\n',
        encoding="utf-8",
    )
    post = parse(csv_path).payload[0]
    assert post.reactions == 9


def test_instagram_saves_are_read(tmp_path):
    """A `Mentések` oszlop csak az Instagram exportjában létezik.

    A mentés nem díszlet: a Mammut júliusi exportjában ötvenhét mentés volt,
    miközben hozzászólás mindössze tizenegy. Ha nem olvassuk be, az Instagram
    egyik legerősebb szándékjelzése hiányzik a pontozásból.
    """
    csv_path = tmp_path / "ig.csv"
    csv_path.write_text(
        "Bejegyzésazonosító,Fiókazonosító,Leírás,"
        '"Közzététel időpontja","Állandó hivatkozás","Bejegyzés típusa",'
        "Megtekintések,Elérés,Kedvelések,Megosztások,Hozzászólások,Mentések\n"
        "181,178,Nyári ajánlat,"
        '"07/03/2026 10:00","https://www.instagram.com/reel/AAA/",REEL,100,80,42,3,5,7\n',
        encoding="utf-8",
    )
    post = parse(csv_path).payload[0]
    assert post.saves == 7


def test_facebook_export_has_no_saves(tmp_path):
    """A Facebook exportjában nincs ilyen oszlop — nulla marad, nem hiba."""
    csv_path = tmp_path / "fb.csv"
    csv_path.write_text(
        'Bejegyzésazonosító,Oldalazonosító,"Oldal neve",Cím,'
        '"Közzététel időpontja","Állandó hivatkozás","Bejegyzés típusa",'
        "Megtekintések,Elérés,Reakciók,Hozzászólások,Megosztások\n"
        '148,100,"Mammut","A poszt",'
        '"07/03/2026 10:00","https://www.facebook.com/100_148",POST,100,80,9,2,1\n',
        encoding="utf-8",
    )
    assert parse(csv_path).payload[0].saves == 0
