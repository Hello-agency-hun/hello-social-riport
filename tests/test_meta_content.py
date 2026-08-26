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
