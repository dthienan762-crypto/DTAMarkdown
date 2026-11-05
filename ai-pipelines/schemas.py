"""
DTAMarkdown Studio - Multimodal AI Pipelines Schemas
Pydantic v2 schemas and models matching docs/specs/api_contract.yaml and PROJECT.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
import uuid

from pydantic import BaseModel, Field, field_validator


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


class PipelineResult(BaseModel):
    """In-process pipeline result passed between /ai-pipelines/ and /backend/."""
    success: bool = Field(..., description="Whether conversion succeeded.")
    pipeline: PipelineType = Field(..., description="Pipeline type executed.")
    markdown: str = Field(..., description="Resulting markdown content.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary.")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings.")
    duration_ms: float = Field(default=0.0, description="Processing latency in ms.")
    job_id: Optional[str] = Field(default=None, description="Job identifier if bound.")

    model_config = {
        "use_enum_values": True,
    }

    def to_conversion_result(self) -> ConversionResult:
        """Helper to convert to OpenAPI ConversionResult."""
        meta_obj = None
        if self.metadata:
            meta_obj = ConversionMetadata(
                word_count=self.metadata.get("word_count"),
                character_count=self.metadata.get("character_count"),
                estimated_read_time=self.metadata.get("estimated_read_time"),
                duration_ms=self.metadata.get("duration_ms", self.duration_ms),
                engine_used=self.metadata.get("engine_used"),
                tags=self.metadata.get("tags", []),
                warnings=self.warnings or self.metadata.get("warnings", []),
                toc=self.metadata.get("toc"),
            )
        return ConversionResult(
            job_id=self.job_id,
            success=self.success,
            pipeline=self.pipeline,
            markdown=self.markdown,
            metadata=meta_obj,
            warnings=self.warnings,
            duration_ms=self.duration_ms,
        )


class StreamChunk(BaseModel):
    """
    Unified streaming event emitted by async pipeline generators.
    Directly maps to WebSocketStatusFrame, WebSocketChunkFrame, WebSocketCompleteFrame,
    or WebSocketErrorFrame.
    """
    event: Literal["status", "chunk", "complete", "error"] = Field(
        ..., description="Event type discriminator."
    )
    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Associated job UUID."
    )
    # Status frame fields
    stage: Optional[str] = Field(default=None, description="Current processing stage identifier.")
    progress: Optional[int] = Field(default=None, ge=0, le=100, description="Progress percentage 0-100.")
    message: Optional[str] = Field(default=None, description="Human readable message or diagnostic.")
    # Chunk frame fields
    delta: Optional[str] = Field(default=None, description="Incremental Markdown text delta.")
    index: Optional[int] = Field(default=None, ge=0, description="Incremental chunk sequence index.")
    # Complete frame fields
    markdown: Optional[str] = Field(default=None, description="Full accumulated Markdown document.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Summary metadata.")
    # Error frame fields
    code: Optional[str] = Field(default=None, description="Standardized error code.")
    recoverable: Optional[bool] = Field(default=None, description="Whether error is recoverable.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="ISO 8601 UTC timestamp."
    )

    model_config = {
        "extra": "ignore",
    }

    def to_ws_dict(self) -> Dict[str, Any]:
        """Convert chunk into exact dictionary for WebSocket frame transmission."""
        base = {
            "event": self.event,
            "job_id": self.job_id,
            "timestamp": self.timestamp,
        }
        if self.event == "status":
            base["stage"] = self.stage or "processing"
            base["progress"] = self.progress if self.progress is not None else 0
            base["message"] = self.message or ""
        elif self.event == "chunk":
            base["delta"] = self.delta or ""
            base["index"] = self.index if self.index is not None else 0
        elif self.event == "complete":
            base["markdown"] = self.markdown or ""
            base["metadata"] = self.metadata or {}
        elif self.event == "error":
            base["code"] = self.code or "PIPELINE_ERROR"
            base["message"] = self.message or "An error occurred during pipeline execution."
            base["recoverable"] = self.recoverable if self.recoverable is not None else False
        return base


# Custom Domain Exceptions
class PipelineError(Exception):
    """Base exception for all multimodal conversion pipeline errors."""
    def __init__(self, message: str, code: str = "PIPELINE_ERROR", recoverable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.recoverable = recoverable


class DegradedInputError(PipelineError):
    """Raised when input image/audio is degraded beyond recovery."""
    def __init__(self, message: str = "Input media is degraded or unreadable.", code: str = "DEGRADED_INPUT"):
        super().__init__(message, code=code, recoverable=False)


class UnsupportedFormatError(PipelineError):
    """Raised when uploaded file format or MIME type cannot be parsed."""
    def __init__(self, message: str = "Unsupported media file format.", code: str = "UNSUPPORTED_MEDIA_TYPE"):
        super().__init__(message, code=code, recoverable=False)


class EmptyFileError(PipelineError):
    """Raised when uploaded file is empty (0 bytes)."""
    def __init__(self, message: str = "Uploaded file contains 0 bytes.", code: str = "EMPTY_FILE"):
        super().__init__(message, code=code, recoverable=False)
