from pipeline.textio import read_lines


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
