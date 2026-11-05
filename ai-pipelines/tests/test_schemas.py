"""
Unit tests for AI Pipelines Schemas (/ai-pipelines/schemas.py)
Validates Pydantic v2 model attributes, defaults, WebSocket frame conversions,
and exception classes.
"""

from pathlib import Path
import sys
import uuid
import pytest

PIPELINES_DIR = Path(__file__).resolve().parent.parent
if str(PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINES_DIR))

from schemas import (
    ConversionMetadata,
    ConversionOptions,
    ConversionResult,
    DegradedInputError,
    EmptyFileError,
    JobStatus,
    PipelineError,
    PipelineResult,
    PipelineType,
    PreferredEngine,
    StreamChunk,
    UnsupportedFormatError,
)


def test_pipeline_type_and_job_status_enums():
    assert PipelineType.VISION_OCR.value == "vision_ocr"
    assert PipelineType.VOICE_STT.value == "voice_stt"
    assert PipelineType.TEXT_NORMALIZE.value == "text_normalize"
    assert PipelineType.AUTO.value == "auto"

    assert JobStatus.QUEUED.value == "QUEUED"
    assert JobStatus.PROCESSING.value == "PROCESSING"
    assert JobStatus.STREAMING.value == "STREAMING"
    assert JobStatus.COMPLETED.value == "COMPLETED"
    assert JobStatus.FAILED.value == "FAILED"
    assert JobStatus.CANCELLED.value == "CANCELLED"


def test_conversion_options_defaults():
    opts = ConversionOptions()
    assert opts.extract_tables is True
    assert opts.extract_math is True
    assert opts.generate_toc is True
    assert opts.extract_tags is True
    assert opts.timestamp_silence_threshold == 2.0
    assert opts.preferred_engine == PreferredEngine.AUTO.value


def test_conversion_options_validation():
    # Valid bounds
    opts = ConversionOptions(timestamp_silence_threshold=5.0)
    assert opts.timestamp_silence_threshold == 5.0

    # Invalid bounds (< 0.5 or > 10.0)
    with pytest.raises(Exception):
        ConversionOptions(timestamp_silence_threshold=0.1)

    with pytest.raises(Exception):
        ConversionOptions(timestamp_silence_threshold=15.0)


def test_pipeline_result_to_conversion_result():
    res = PipelineResult(
        success=True,
        pipeline=PipelineType.VISION_OCR,
        markdown="# Title\n\nContent",
        metadata={
            "word_count": 50,
            "character_count": 300,
            "estimated_read_time": "1 min",
            "duration_ms": 125.0,
            "engine_used": "PyMuPDF Fast-Path",
            "tags": ["Test"],
            "warnings": [],
            "toc": "- [Title](#title)"
        },
        warnings=[],
        duration_ms=125.0,
        job_id=str(uuid.uuid4())
    )

    conv_res = res.to_conversion_result()
    assert conv_res.success is True
    assert conv_res.pipeline == PipelineType.VISION_OCR
    assert conv_res.metadata is not None
    assert conv_res.metadata.word_count == 50
    assert conv_res.metadata.engine_used == "PyMuPDF Fast-Path"


def test_stream_chunk_ws_dict_serialization():
    jid = str(uuid.uuid4())

    # 1. Status chunk
    status_chunk = StreamChunk(
        event="status",
        job_id=jid,
        stage="ocr_processing",
        progress=45,
        message="Extracting tables..."
    )
    ws_status = status_chunk.to_ws_dict()
    assert ws_status["event"] == "status"
    assert ws_status["job_id"] == jid
    assert ws_status["stage"] == "ocr_processing"
    assert ws_status["progress"] == 45
    assert ws_status["message"] == "Extracting tables..."

    # 2. Chunk frame
    data_chunk = StreamChunk(
        event="chunk",
        job_id=jid,
        delta="| A | B |\n",
        index=2
    )
    ws_chunk = data_chunk.to_ws_dict()
    assert ws_chunk["event"] == "chunk"
    assert ws_chunk["delta"] == "| A | B |\n"
    assert ws_chunk["index"] == 2

    # 3. Complete frame
    comp_chunk = StreamChunk(
        event="complete",
        job_id=jid,
        markdown="# Finished",
        metadata={"word_count": 10}
    )
    ws_comp = comp_chunk.to_ws_dict()
    assert ws_comp["event"] == "complete"
    assert ws_comp["markdown"] == "# Finished"

    # 4. Error frame
    err_chunk = StreamChunk(
        event="error",
        job_id=jid,
        code="DEGRADED_IMAGE",
        message="Contrast too low",
        recoverable=False
    )
    ws_err = err_chunk.to_ws_dict()
    assert ws_err["event"] == "error"
    assert ws_err["code"] == "DEGRADED_IMAGE"
    assert ws_err["recoverable"] is False


def test_custom_exceptions():
    e1 = PipelineError("Generic", code="CUSTOM_CODE")
    assert e1.code == "CUSTOM_CODE"

    e2 = DegradedInputError("Low quality")
    assert e2.code == "DEGRADED_INPUT"
    assert isinstance(e2, PipelineError)

    e3 = UnsupportedFormatError("Bad format")
    assert e3.code == "UNSUPPORTED_MEDIA_TYPE"

    e4 = EmptyFileError("0 bytes")
    assert e4.code == "EMPTY_FILE"
