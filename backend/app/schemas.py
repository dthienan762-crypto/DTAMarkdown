"""
DTAMarkdown Studio - Backend Pydantic v2 Schemas.
Strictly conforms to docs/specs/api_contract.yaml and docs/specs/core_principles.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
import uuid

from pydantic import BaseModel, Field, field_validator


def utc_now_iso() -> str:
    """Return ISO 8601 UTC timestamp ending in Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PipelineType(str, Enum):
    """Multimodal conversion pipeline identifier."""
    AUTO = "auto"
    VISION_OCR = "vision_ocr"
    VOICE_STT = "voice_stt"
    TEXT_NORMALIZE = "text_normalize"


class JobStatus(str, Enum):
    """Lifecycle state of an asynchronous processing job."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PreferredEngine(str, Enum):
    """Supported conversion engines."""
    AUTO = "auto"
    GEMINI = "gemini"
    LOCAL_ONNX = "local_onnx"
    PYMUPDF_FAST = "pymupdf_fast"


class ConversionOptions(BaseModel):
    """Configuration options for multimodal conversion."""
    extract_tables: bool = Field(
        default=True,
        description="Detect tabular data and format into GFM tables."
    )
    extract_math: bool = Field(
        default=True,
        description="Detect math formulas and enclose in KaTeX delimiters ($..$, $$..$$)."
    )
    generate_toc: bool = Field(
        default=True,
        description="Auto-generate hierarchical Table of Contents with slug anchors."
    )
    extract_tags: bool = Field(
        default=True,
        description="Extract keyword tags and generate YAML frontmatter."
    )
    timestamp_silence_threshold: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Audio pause duration in seconds to trigger a new timestamped paragraph."
    )
    preferred_engine: PreferredEngine = Field(
        default=PreferredEngine.AUTO,
        description="Preferred underlying conversion engine."
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": True,
    }


class ConversionMetadata(BaseModel):
    """Metadata summary associated with converted Markdown."""
    word_count: Optional[int] = Field(default=None, description="Total word count of document.")
    character_count: Optional[int] = Field(default=None, description="Total character count.")
    estimated_read_time: Optional[str] = Field(default=None, description="Human-readable reading time.")
    duration_ms: Optional[float] = Field(default=None, description="Processing duration in milliseconds.")
    engine_used: Optional[str] = Field(default=None, description="Name of the engine used for conversion.")
    tags: List[str] = Field(default_factory=list, description="Extracted keyword tags.")
    warnings: List[str] = Field(default_factory=list, description="Conversion warnings or non-fatal anomalies.")
    toc: Optional[str] = Field(default=None, description="Rendered markdown Table of Contents.")

    model_config = {
        "extra": "ignore",
    }


class ConversionResult(BaseModel):
    """Strict conversion result conforming to api_contract.yaml."""
    job_id: Optional[str] = Field(default=None, description="Job UUIDv4 string.")
    success: bool = Field(..., description="Whether conversion succeeded.")
    pipeline: PipelineType = Field(..., description="Pipeline type used.")
    markdown: str = Field(..., description="Pristine GitHub Flavored Markdown output.")
    metadata: Optional[ConversionMetadata] = Field(default=None, description="Detailed metadata.")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings.")
    duration_ms: float = Field(..., description="Execution duration in milliseconds.")

    model_config = {
        "use_enum_values": True,
    }


class ErrorResponse(BaseModel):
    """Standard error response payload."""
    code: str = Field(..., description="Machine-readable error code.", json_schema_extra={"example": "INVALID_FILE_FORMAT"})
    message: str = Field(..., description="Human-readable error description.")
    details: Optional[Any] = Field(default=None, description="Additional context or validation details.")
    timestamp: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC timestamp.")


class JobCreatedResponse(BaseModel):
    """Response returned upon successful file staging and job creation."""
    job_id: str = Field(..., description="Job UUIDv4 string.")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Initial job status.")
    pipeline: PipelineType = Field(..., description="Inferred or requested pipeline type.")
    created_at: str = Field(default_factory=utc_now_iso, description="ISO 8601 UTC timestamp.")
    stream_url: str = Field(..., description="WebSocket stream URL for real-time chunks.")

    model_config = {
        "use_enum_values": True,
    }


class JobDetailResponse(BaseModel):
    """Detailed job status and result payload."""
    job_id: str = Field(..., description="Unique UUIDv4 job identifier.")
    status: JobStatus = Field(..., description="Current job status.")
    pipeline: PipelineType = Field(..., description="Pipeline type.")
    progress: Optional[int] = Field(default=0, ge=0, le=100, description="Job progress percentage.")
    created_at: str = Field(..., description="Creation ISO 8601 UTC timestamp.")
    completed_at: Optional[str] = Field(default=None, description="Completion ISO 8601 UTC timestamp.")
    result: Optional[ConversionResult] = Field(default=None, description="Final conversion result.")
    error: Optional[ErrorResponse] = Field(default=None, description="Error payload if failed.")

    model_config = {
        "use_enum_values": True,
    }


class TextConvertRequest(BaseModel):
    """Request payload for synchronous text/HTML conversion."""
    raw_text: str = Field(..., description="Unstructured raw text or messy HTML input.")
    pipeline_type: PipelineType = Field(
        default=PipelineType.TEXT_NORMALIZE,
        description="Target pipeline (defaults to text_normalize)."
    )
    options: Optional[ConversionOptions] = Field(
        default=None,
        description="Optional conversion options."
    )

    model_config = {
        "use_enum_values": True,
    }


class PdfExportRequest(BaseModel):
    """Request payload for compiling Markdown into PDF."""
    markdown: str = Field(..., description="Source Markdown text with KaTeX formulas and GFM tables.")
    title: Optional[str] = Field(default="Document", description="Document title for PDF header.")
    page_size: Optional[str] = Field(default="A4", description="Page size: A4, Letter, Legal.")
    orientation: Optional[str] = Field(default="portrait", description="Orientation: portrait, landscape.")
    include_styles: Optional[bool] = Field(default=True, description="Embed typography styling and borders.")


class EngineAvailability(BaseModel):
    """Availability status of conversion engines."""
    pymupdf_fast: bool = Field(default=True)
    gemini_vision: bool = Field(default=False)
    rapidocr_onnx: bool = Field(default=True)
    faster_whisper: bool = Field(default=False)
    speech_recognition: bool = Field(default=True)


class HealthResponse(BaseModel):
    """System health check and engine telemetry response."""
    status: str = Field(default="HEALTHY")
    version: str = Field(default="1.0.0")
    uptime_seconds: float = Field(...)
    engines_available: EngineAvailability = Field(default_factory=EngineAvailability)
    active_jobs: int = Field(default=0)


# --- WebSocket Streaming Frame Schemas ---

class WebSocketStatusFrame(BaseModel):
    """Status frame indicating stage progress."""
    event: Literal["status"] = "status"
    job_id: str
    stage: str
    progress: int = Field(ge=0, le=100)
    message: str
    timestamp: str = Field(default_factory=utc_now_iso)


class WebSocketChunkFrame(BaseModel):
    """Chunk frame delivering incremental Markdown delta."""
    event: Literal["chunk"] = "chunk"
    job_id: str
    delta: str
    index: int = Field(ge=0)
    timestamp: str = Field(default_factory=utc_now_iso)


class WebSocketCompleteFrame(BaseModel):
    """Complete frame delivering full markdown and final metadata."""
    event: Literal["complete"] = "complete"
    job_id: str
    markdown: str
    metadata: Optional[ConversionMetadata] = None
    timestamp: str = Field(default_factory=utc_now_iso)


class WebSocketErrorFrame(BaseModel):
    """Error frame delivering standardized failure diagnostic."""
    event: Literal["error"] = "error"
    job_id: str
    code: str
    message: str
    recoverable: bool = False
    timestamp: str = Field(default_factory=utc_now_iso)
