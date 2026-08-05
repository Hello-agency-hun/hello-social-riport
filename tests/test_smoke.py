def test_pipeline_importable():
    import pipeline

    assert pipeline is not None


def test_fixture_present(input_dir):
    files = list(input_dir.iterdir())
    assert len(files) == 11
