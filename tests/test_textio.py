from pipeline.textio import read_csv_rows, read_lines


def test_utf16_daily_csv_is_decoded(input_file):
    lines = read_lines(input_file("Felkeresések.csv"))
    assert lines[0].startswith("sep=")
    assert lines[1].strip('"') == "Facebook-felkeresések"


def test_utf8_csv_is_decoded(input_file):
    lines = read_lines(input_file("Kampányok"))
    assert "Kampány neve" in lines[0]


def test_blank_lines_are_dropped(input_file):
    lines = read_lines(input_file("Követők.csv"))
    assert all(line.strip() for line in lines)


def test_multiline_campaign_name_keeps_its_blank_line(input_file):
    """A kampánynév bekezdéshatára nem tűnhet el a beolvasás során."""
    names = [row["Kampány neve"] for row in read_csv_rows(input_file("Kampányok"))]
    assert any("💫\n\nTe kit" in name for name in names)


def test_multiline_caption_paragraphs_are_not_glued(input_file):
    """Enélkül a riportban `tartunk.A többi napon` jelenne meg."""
    captions = [row["Cím"] for row in read_csv_rows(input_file("Jul-01-2026"))]
    opening = next(c for c in captions if c.startswith("Kedves Vendégeink"))
    assert "zárva tartunk.\nA többi napon" in opening


def test_csv_row_count_is_unaffected_by_embedded_newlines(input_file):
    assert len(read_csv_rows(input_file("Kampányok"))) == 29
    assert len(read_csv_rows(input_file("Jul-01-2026"))) == 16
