import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def reel():
    return json.loads((FIXTURES / "reel_solve.json").read_text())
