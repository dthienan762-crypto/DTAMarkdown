"""
DTAMarkdown Studio - Conversion REST Endpoints.
Conforms strictly to docs/specs/api_contract.yaml.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import time
from typing import Optional
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.schemas import (
    ConversionMetadata,
    ConversionOptions,
    ConversionResult,
    ErrorResponse,
    JobCreatedResponse,
    JobDetailResponse,
    JobStatus,
    PipelineType,
    TextConvertRequest,
    utc_now_iso,
)
from backend.app.services.job_manager import job_manager
from backend.app.services.temp_manager import (
    EmptyFilePayloadException,
    PayloadTooLargeException,
    get_staging_dir,
    sanitize_filename,
)

logger = logging.getLogger("dtamarkdown.routes.convert")

router = APIRouter(prefix="/api/v1", tags=["conversion"])


def infer_pipeline_from_file(filename: str, content_type: Optional[str] = None) -> PipelineType:
    """Infer target pipeline from filename extension and MIME type."""
    ext = Path(filename).suffix.lower()
    ct = (content_type or "").lower()

    # Audio extensions / MIME
    audio_exts = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".aac", ".wma"}
    if ext in audio_exts or "audio" in ct:
        return PipelineType.VOICE_STT

    # Text / HTML extensions / MIME
    text_exts = {".html", ".htm", ".txt", ".md"}
    if ext in text_exts or "text/html" in ct or "text/plain" in ct:
        return PipelineType.TEXT_NORMALIZE

    # Document / image extensions
    return PipelineType.VISION_OCR


@router.post(
    "/convert/file",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload file for multimodal conversion",
)
async def convert_file(
    file: UploadFile = File(..., description="Uploaded document, image, or audio binary file."),
    pipeline_type: Optional[str] = Form("auto", description="Target pipeline: auto, vision_ocr, voice_stt, text_normalize."),
    options_json: Optional[str] = Form(None, description="Optional JSON-encoded ConversionOptions object."),
):
    """
    Accepts documents (PDF), images, or audio recordings.
    Validates size and emptiness, stages securely, queues asynchronous job,
    and returns 202 Accepted with job ID and WebSocket stream URL.
    """
    # 1. Parse and validate options_json if provided
    conversion_options = ConversionOptions()
    if options_json and options_json.strip():
        try:
            opts_dict = json.loads(options_json)
            conversion_options = ConversionOptions(**opts_dict)
        except Exception as e:
            logger.warning("Malformed options_json: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "MALFORMED_OPTIONS_JSON", "message": f"Invalid options_json: {str(e)}"},
            )

    # 2. Determine target pipeline
    target_pipeline = PipelineType.AUTO
    if pipeline_type:
        try:
            target_pipeline = PipelineType(pipeline_type.lower())
        except ValueError:
            target_pipeline = PipelineType.AUTO

    if target_pipeline == PipelineType.AUTO:
        target_pipeline = infer_pipeline_from_file(file.filename or "upload.bin", file.content_type)

    # 3. Determine size limit based on inferred/requested pipeline
    is_audio = (target_pipeline == PipelineType.VOICE_STT)
    max_allowed_bytes = settings.MAX_AUDIO_SIZE_BYTES if is_audio else settings.MAX_DOCUMENT_SIZE_BYTES

    # 4. Secure Staging with size & emptiness validation
    job_id = str(uuid.uuid4())
    staging_dir = get_staging_dir()
    clean_name = sanitize_filename(file.filename or "upload.bin")
    timestamp_ms = int(time.time() * 1000)
    staged_filename = f"{job_id}_{timestamp_ms}_{clean_name}"
    staged_path = staging_dir / staged_filename

    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB buffer

    try:
        file_too_large = False
        with open(staged_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_allowed_bytes:
                    file_too_large = True
                    break
                f.write(chunk)

        if file_too_large:
            staged_path.unlink(missing_ok=True)
            limit_mb = max_allowed_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail={
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"File exceeds maximum allowed size of {limit_mb}MB for this media type.",
                },
            )

        if total_bytes == 0:
            staged_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EMPTY_FILE_PAYLOAD", "message": "Uploaded file contains 0 bytes."},
            )

    except HTTPException:
        raise
    except Exception as e:
        if staged_path.exists():
            try:
                staged_path.unlink(missing_ok=True)
            except Exception:
                pass
        logger.error("Error staging uploaded file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "STAGING_ERROR", "message": "Failed to stage uploaded file."},
        )

    # 5. Create Job and queue execution in JobManager
    await job_manager.create_job(
        pipeline_type=target_pipeline,
        options=conversion_options,
        file_path=staged_path,
        job_id=job_id,
    )
    job_manager.submit_job(job_id)

    stream_url = f"/api/v1/ws/stream/{job_id}"
    logger.info("Queued job %s [pipeline=%s, size=%d bytes]", job_id, target_pipeline.value, total_bytes)

    return JobCreatedResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        pipeline=target_pipeline,
        created_at=utc_now_iso(),
        stream_url=stream_url,
    )


@router.post(
    "/convert/text",
    response_model=ConversionResult,
    status_code=status.HTTP_200_OK,
    summary="Convert raw text or HTML to Markdown",
)
async def convert_text(payload: TextConvertRequest):
    """
    Synchronously normalizes unstructured raw text or messy HTML into standard GFM Markdown,
    resolving tables, shielding math delimiters ($..$, $$..$$), and generating TOC/tags.
    """
    raw_text = payload.raw_text
    if not raw_text or not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_TEXT_PAYLOAD", "message": "Raw text input cannot be empty."},
        )

    start_time = time.time()
    options = payload.options or ConversionOptions()

    # Execute text normalization via genuine text_engine
    engine_name = "Text Normalizer Engine"

    try:
        from text_engine import TextNormalizer, TOCGenerator, TagExtractor
        normalizer = TextNormalizer()
        res = normalizer.normalize(
            raw_text,
            extract_tables=options.extract_tables,
            extract_math=options.extract_math,
        )
        if isinstance(res, tuple):
            markdown_out, _ = res
        else:
            markdown_out = res

        import re
        markdown_out = re.sub(r"\|\s*---\s*(\|\s*---\s*)+\|", lambda m: re.sub(r"\s+", "", m.group(0)), markdown_out)

        toc_str = None
        if options.generate_toc:
            toc_str = TOCGenerator.generate_toc(markdown_out)
            if toc_str:
                markdown_out = TOCGenerator.inject_toc(markdown_out, toc_str)

        w_count, c_count = TagExtractor.calculate_word_and_char_count(markdown_out)
        read_time = TagExtractor.estimate_read_time(w_count)
        tags = TagExtractor.extract_tags(markdown_out) if options.extract_tags else ["markdown", "text_normalize"]

    except Exception as e:
        logger.error("convert_text normalization error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "NORMALIZATION_ERROR", "message": f"Text normalization failed: {e}"},
        )

    duration_ms = round((time.time() - start_time) * 1000, 2)
    word_count = len(markdown_out.split())
    character_count = len(markdown_out)

    metadata = ConversionMetadata(
        word_count=word_count,
        character_count=character_count,
        estimated_read_time=f"{max(1, word_count // 200)} min",
        duration_ms=duration_ms,
        engine_used=engine_name,
        tags=tags,
        toc=toc_str if options.generate_toc else None,
    )

    return ConversionResult(
        job_id=str(uuid.uuid4()),
        success=True,
        pipeline=payload.pipeline_type,
        markdown=markdown_out,
        metadata=metadata,
        warnings=[],
        duration_ms=duration_ms,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve job status and conversion result",
)
async def get_job(job_id: str):
    """
    Polls the execution state of an asynchronous multimodal conversion job.
    Used as fallback when WebSocket is unavailable or after stream disconnect.
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found or expired."},
        )
    return job
