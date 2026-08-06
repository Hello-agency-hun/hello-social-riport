from pipeline.labels import shorten


def test_short_text_is_untouched():
    assert shorten("Séfünk ajánlata!", 40) == "Séfünk ajánlata!"


def test_it_cuts_at_a_word_boundary_not_mid_word():
    """Karakterszámra vágva olyan feliratok születtek, mint „lehet panas”."""
    text = "Heti menünkre most sem lehet panasz, kóstoljátok végig!"
    out = shorten(text, 34)
    assert out.endswith("…")
    assert "panas…" not in out
    assert out.rstrip("…").split()[-1] in text.replace(",", " ").split()


def test_trailing_punctuation_is_dropped_before_the_ellipsis():
    """Ne „roppanósan.…" legyen belőle."""
    out = shorten("Frissen, roppanósan. Ahogy szeretitek!", 20)
    assert out == "Frissen, roppanósan…"


def test_whitespace_is_normalised():
    assert shorten("Két\n\nsor   közte", 40) == "Két sor közte"


def test_a_single_long_word_is_still_cut_hard():
    """Egyetlen hosszú szó ne tüntesse el az egész feliratot."""
    out = shorten("Visszavonhatatlanulmegmagyarazhatatlansag", 20)
    assert out.endswith("…")
    assert len(out) <= 21


def test_empty_input_is_safe():
    assert shorten("", 10) == ""
    assert shorten(None, 10) == ""
