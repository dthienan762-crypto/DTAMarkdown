"""
DTAMarkdown Studio - Production FastAPI Backend Application.
Adheres strictly to docs/specs/api_contract.yaml and docs/specs/core_principles.md.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import importlib.util
import logging
from pathlib import Path
import sys
from typing import AsyncIterator

# Ensure backend/.deps and ai_pipelines alias are registered
backend_dir = Path(__file__).resolve().parent.parent
deps_dir = backend_dir / ".deps"
if deps_dir.exists() and str(deps_dir) not in sys.path:
    sys.path.insert(0, str(deps_dir))

workspace_root = backend_dir.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

ai_pipelines_dir = workspace_root / "ai-pipelines"
if ai_pipelines_dir.exists() and str(ai_pipelines_dir) not in sys.path:
    sys.path.insert(0, str(ai_pipelines_dir))

if ai_pipelines_dir.exists() and "ai_pipelines" not in sys.modules:
    spec = importlib.util.spec_from_file_location("ai_pipelines", str(ai_pipelines_dir / "__init__.py"))
    if spec and spec.loader:
        ai_pipelines_mod = importlib.util.module_from_spec(spec)
        ai_pipelines_mod.__path__ = [str(ai_pipelines_dir)]
        sys.modules["ai_pipelines"] = ai_pipelines_mod
        try:
            spec.loader.exec_module(ai_pipelines_mod)
        except Exception:
            pass

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.routes import (
    convert_router,
    export_router,
    health_router,
    stream_router,
)
from backend.app.schemas import ErrorResponse, utc_now_iso
from backend.app.services.temp_manager import TempReaperService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dtamarkdown.main")

reaper_service = TempReaperService(
    staging_dir=settings.STAGING_DIR,
    interval_seconds=settings.REAPER_INTERVAL_SECONDS,
    max_age_seconds=settings.REAPER_MAX_AGE_SECONDS,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.
    Executes synchronous startup sweep of dtamarkdown_staging,
    spawns the periodic TempReaperService background task,
    and handles graceful termination.
    """
    logger.info("Initializing DTAMarkdown Studio Backend (v%s)...", settings.VERSION)

    # 1. Startup Staging Sweep (Principle 3.4)
    purged = TempReaperService.startup_sweep(settings.STAGING_DIR)
    logger.info("Lifespan startup sweep cleared %d residual file(s).", purged)

    # 2. Start Background Reaper Service (Principle 3.3)
    reaper_service.start()

    yield

    # 3. Graceful Shutdown
    logger.info("Shutting down DTAMarkdown Studio Backend...")
    reaper_service.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Production REST & WebSocket API for DTAMarkdown Studio multimodal conversion.",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API Routers
    app.include_router(convert_router)
    app.include_router(stream_router)
    app.include_router(export_router)
    app.include_router(health_router)

    # Mount static frontend build if present
    if settings.STATIC_DIR and settings.STATIC_DIR.exists() and (settings.STATIC_DIR / "index.html").exists():
        logger.info("Mounting frontend static distribution from: %s", settings.STATIC_DIR)
        app.mount("/", StaticFiles(directory=str(settings.STATIC_DIR), html=True), name="static")

    # Custom Exception Handlers strictly conforming to ErrorResponse schema
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", f"HTTP_{exc.status_code}")
            message = detail.get("message", "An error occurred.")
            details = detail.get("details", None)
        else:
            code = f"HTTP_{exc.status_code}"
            message = str(detail)
            details = None

        error_payload = ErrorResponse(
            code=code,
            message=message,
            details=details,
            timestamp=utc_now_iso(),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_payload = ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request schema validation failed.",
            details=exc.errors(),
            timestamp=utc_now_iso(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload.model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception: %s", exc)
        error_payload = ErrorResponse(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            details={"error_type": type(exc).__name__, "message": str(exc)},
            timestamp=utc_now_iso(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload.model_dump(),
        )

    return app


app = create_app()
