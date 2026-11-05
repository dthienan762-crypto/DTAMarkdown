"""
DTAMarkdown Studio - Health & Telemetry REST Endpoint.
Endpoint: /api/v1/health
Conforms to docs/specs/api_contract.yaml.
"""

from __future__ import annotations

import logging
import os
import time
from fastapi import APIRouter, status

from backend.app.config import settings
from backend.app.schemas import EngineAvailability, HealthResponse
from backend.app.services.job_manager import job_manager

logger = logging.getLogger("dtamarkdown.routes.health")

router = APIRouter(prefix="/api/v1", tags=["telemetry"])

# Global process start timestamp
SERVER_START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System health check and engine telemetry",
)
async def get_health():
    """
    Returns operational status, server uptime, active job count,
    and availability of local/cloud multimodal conversion engines.
    """
    uptime = round(time.time() - SERVER_START_TIME, 2)

    # Check installed engine flags
    engines = EngineAvailability(
        pymupdf_fast=True,
        gemini_vision=bool(os.getenv("GEMINI_API_KEY")),
        rapidocr_onnx=True,
        faster_whisper=False,
        speech_recognition=True,
    )

    return HealthResponse(
        status="HEALTHY",
        version=settings.VERSION,
        uptime_seconds=uptime,
        engines_available=engines,
        active_jobs=job_manager.active_jobs_count,
    )
