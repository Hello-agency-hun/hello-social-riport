from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "larus-2026-07"


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURE


@pytest.fixture
def input_dir() -> Path:
    return FIXTURE / "input"


@pytest.fixture
def input_file(input_dir):
    """Fájl keresése névtöredék alapján — a tesztek ne függjenek a pontos névtől."""

    def _find(fragment: str) -> Path:
        matches = [p for p in input_dir.iterdir() if fragment in p.name]
        assert len(matches) == 1, f"{fragment}: {len(matches)} találat"
        return matches[0]

    return _find
