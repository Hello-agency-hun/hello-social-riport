def test_pipeline_importable():
    import pipeline

    assert pipeline is not None


def test_fixture_present(input_dir):
    files = list(input_dir.iterdir())
    assert len(files) == 11


def test_fixture_line_endings_are_not_rewritten(input_dir):
    """A git autocrlf Windows-on átírta a fixture-t LF-ről CRLF-re.

    A tesztadat a valós Meta export bájtpontos másolata — ha bármi átírja,
    megszűnik bizonyíték lenni. A .gitattributes `-text` védi; ez a teszt őrzi.
    """
    utf8_csvs = [
        path
        for path in input_dir.glob("*.csv")
        if not path.read_bytes().startswith((b"\xff\xfe", b"\xfe\xff"))
    ]
    assert utf8_csvs, "legalább egy UTF-8 CSV-nek lennie kell a fixture-ben"
    for path in utf8_csvs:
        assert b"\r\n" not in path.read_bytes(), f"{path.name}: CRLF-re konvertálódott"
