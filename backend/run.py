"""
DTAMarkdown Studio - Server Entrypoint.
"""

import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add backend and backend/.deps to sys.path
backend_dir = Path(__file__).resolve().parent
deps_dir = backend_dir / ".deps"
if deps_dir.exists() and str(deps_dir) not in sys.path:
    sys.path.insert(0, str(deps_dir))

workspace_root = backend_dir.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

ai_pipelines_dir = workspace_root / "ai-pipelines"
if ai_pipelines_dir.exists() and "ai_pipelines" not in sys.modules:
    import importlib.util
    spec = importlib.util.spec_from_file_location("ai_pipelines", str(ai_pipelines_dir / "__init__.py"))
    if spec and spec.loader:
        ai_pipelines_mod = importlib.util.module_from_spec(spec)
        ai_pipelines_mod.__path__ = [str(ai_pipelines_dir)]
        sys.modules["ai_pipelines"] = ai_pipelines_mod
        try:
            spec.loader.exec_module(ai_pipelines_mod)
        except Exception:
            pass

import uvicorn
from backend.app.config import settings

if __name__ == "__main__":
    should_open = "--open" in sys.argv or "-o" in sys.argv or True

    if should_open:
        def _open_browser():
            time.sleep(1.2)
            url = f"http://localhost:{settings.PORT}/"
            try:
                webbrowser.open_new_tab(url)
            except Exception:
                pass

        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
