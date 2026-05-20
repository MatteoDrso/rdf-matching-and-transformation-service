from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from src.core import karma_runner

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _karma_available() -> bool:
    try:
        karma_runner._resolve_jar()
        karma_runner._resolve_java()
    except FileNotFoundError:
        return False
    return True


requires_karma = pytest.mark.skipif(
    not _karma_available(),
    reason="Requires Karma JAR (lib/karma-offline-*-shaded.jar) and a working Java runtime",
)
