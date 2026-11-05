"""
DTAMarkdown Studio - Test Configuration and Fixtures.
"""

import sys
from pathlib import Path
import pytest

# Ensure backend/.deps and workspace root are in sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEPS_DIR = _BACKEND_DIR / ".deps"
if _DEPS_DIR.exists() and str(_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPS_DIR))

_ROOT_DIR = _BACKEND_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from starlette.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client
