"""
DTAMarkdown Studio - Backend Configuration.
"""

import os
import sys
from pathlib import Path
import tempfile
from typing import List, Optional

# Bridge ai-pipelines and backend/.deps into sys.path
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
_AI_PIPELINES_DIR = _WORKSPACE_ROOT / "ai-pipelines"
if _AI_PIPELINES_DIR.exists() and str(_AI_PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINES_DIR))

_BACKEND_DEPS = _WORKSPACE_ROOT / "backend" / ".deps"
if _BACKEND_DEPS.exists() and str(_BACKEND_DEPS) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DEPS))


class Settings:
    """Application configuration settings."""

    # Server Settings
    APP_NAME: str = "DTAMarkdown Studio API"
    VERSION: str = "1.0.0"
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "*",
    ]

    # Staging & Temp File Lifecycle
    STAGING_DIR: Path = Path(tempfile.gettempdir()) / "dtamarkdown_staging"
    REAPER_INTERVAL_SECONDS: int = 600  # 10 minutes
    REAPER_MAX_AGE_SECONDS: int = 1800  # 30 minutes

    # Payload Size Limits (Principle 3 & api_contract.yaml - Up to 200 MB)
    MAX_DOCUMENT_SIZE_BYTES: int = 200 * 1024 * 1024  # 200 MB
    MAX_AUDIO_SIZE_BYTES: int = 200 * 1024 * 1024   # 200 MB

    # Concurrency & Resilience (Principle 2)
    MAX_CONCURRENT_JOBS: int = 4
    DETACHED_GRACE_PERIOD_SECONDS: int = 60

    # Frontend Static Distribution Directory
    STATIC_DIR: Optional[Path] = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


settings = Settings()
