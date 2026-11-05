"""
DTAMarkdown Studio - Root Integration Test Fixtures.
"""

import sys
from pathlib import Path
import pytest

# Ensure backend/.deps, ai-pipelines, and workspace root are in sys.path
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_DEPS_DIR = _WORKSPACE_ROOT / "backend" / ".deps"
if _DEPS_DIR.exists() and str(_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPS_DIR))

_AI_PIPELINES_DIR = _WORKSPACE_ROOT / "ai-pipelines"
if _AI_PIPELINES_DIR.exists() and str(_AI_PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINES_DIR))

if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from starlette.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client
