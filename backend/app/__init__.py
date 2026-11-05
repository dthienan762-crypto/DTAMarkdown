"""
DTAMarkdown Studio - Backend Application Package.
"""

import sys
from pathlib import Path

# Ensure backend/.deps is available in sys.path
_DEPS_DIR = Path(__file__).resolve().parent.parent / ".deps"
if _DEPS_DIR.exists() and str(_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPS_DIR))

# Ensure root workspace and ai-pipelines are in sys.path
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.append(str(_ROOT_DIR))

_AI_PIPELINES_DIR = _ROOT_DIR / "ai-pipelines"
if _AI_PIPELINES_DIR.exists() and str(_AI_PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINES_DIR))
