"""
DTAMarkdown Studio - Unified Multimodal AI Pipeline Runner
Single entrypoint coordinating Vision OCR, Voice STT, and Text Normalization engines.
Exposes async run_pipeline and stream_pipeline matching PROJECT.md interface contracts.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import time
from typing import AsyncIterator, Dict, List, Optional
import uuid

from schemas import (
    ConversionMetadata,
    ConversionOptions,
    DegradedInputError,
    EmptyFileError,
    PipelineError,
    PipelineResult,
    PipelineType,
    StreamChunk,
    UnsupportedFormatError,
)
from text_engine import TableNormalizer, TextNormalizer, TOCGenerator, TagExtractor
from vision_ocr import VisionOCREngine
from voice_stt import VoiceSTTEngine


# File extension to pipeline type mappings
VISION_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
VOICE_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
TEXT_EXTENSIONS = {".txt", ".html", ".htm", ".md"}


def detect_pipeline_type(file_path: Path) -> PipelineType:
    """Infers the appropriate multimodal pipeline based on file extension and headers."""
    suffix = file_path.suffix.lower()

    if suffix in VISION_EXTENSIONS:
        return PipelineType.VISION_OCR
    elif suffix in VOICE_EXTENSIONS:
        return PipelineType.VOICE_STT
    elif suffix in TEXT_EXTENSIONS:
        return PipelineType.TEXT_NORMALIZE
    else:
        raise UnsupportedFormatError(
            f"Unsupported file format '{suffix}' for file '{file_path.name}'. "
            f"Supported extensions: {sorted(VISION_EXTENSIONS | VOICE_EXTENSIONS | TEXT_EXTENSIONS)}"
        )


class PipelineRunner:
    """
    Central runner managing multimodal conversion engine lifecycles.
    """

    def __init__(self):
        self.vision_engine = VisionOCREngine()
        self.voice_engine = VoiceSTTEngine()
        self.text_normalizer = TextNormalizer()

    def run_text_normalize(
        self,
        raw_text: str,
        options: ConversionOptions,
        job_id: Optional[str] = None
    ) -> PipelineResult:
        """Processes raw text or HTML through text normalization engine."""
        start_time = time.perf_counter()
        jid = job_id or str(uuid.uuid4())

        if not raw_text or not raw_text.strip():
            raise EmptyFileError("Text input is empty.")

        normalized_md, warnings = self.text_normalizer.normalize(
            raw_text,
            extract_tables=options.extract_tables,
            extract_math=options.extract_math
        )

        toc_str = None
        if options.generate_toc:
            toc_str = TOCGenerator.generate_toc(normalized_md)
            if toc_str:
                normalized_md = TOCGenerator.inject_toc(normalized_md, toc_str)

        w_count, c_count = TagExtractor.calculate_word_and_char_count(normalized_md)
        read_time = TagExtractor.estimate_read_time(w_count)
        tags = TagExtractor.extract_tags(normalized_md) if options.extract_tags else []

        if options.extract_tags and w_count > 0:
            doc_title = TagExtractor.extract_document_title(normalized_md)
            fm = TagExtractor.generate_frontmatter(doc_title, tags, w_count, read_time)
            normalized_md = TagExtractor.inject_frontmatter(normalized_md, fm)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = {
            "word_count": w_count,
            "character_count": c_count,
            "estimated_read_time": read_time,
            "duration_ms": round(elapsed_ms, 2),
            "engine_used": "BS4 & AST Text Normalizer",
            "tags": tags,
            "warnings": warnings,
            "toc": toc_str,
        }

        return PipelineResult(
            success=True,
            pipeline=PipelineType.TEXT_NORMALIZE,
            markdown=normalized_md,
            metadata=metadata,
            warnings=warnings,
            duration_ms=round(elapsed_ms, 2),
            job_id=jid
        )

    async def run_pipeline(
        self,
        file_path: Path,
        pipeline_type: PipelineType = PipelineType.AUTO,
        options: Optional[ConversionOptions] = None,
        job_id: Optional[str] = None
    ) -> PipelineResult:
        """
        Executes the designated multimodal pipeline asynchronously in a worker thread.
        """
        opts = options or ConversionOptions()
        resolved_pipeline = pipeline_type

        if resolved_pipeline == PipelineType.AUTO:
            resolved_pipeline = detect_pipeline_type(file_path)

        jid = job_id or str(uuid.uuid4())

        if resolved_pipeline == PipelineType.VISION_OCR:
            res = await asyncio.to_thread(self.vision_engine.convert, file_path, opts)
            res.job_id = jid
            return res

        elif resolved_pipeline == PipelineType.VOICE_STT:
            res = await asyncio.to_thread(self.voice_engine.convert, file_path, opts)
            res.job_id = jid
            return res

        elif resolved_pipeline == PipelineType.TEXT_NORMALIZE:
            raw_text = await asyncio.to_thread(file_path.read_text, "utf-8", "replace")
            return await asyncio.to_thread(self.run_text_normalize, raw_text, opts, jid)

        else:
            raise UnsupportedFormatError(f"Unknown pipeline type: {resolved_pipeline}")

    async def stream_pipeline(
        self,
        file_path: Path,
        pipeline_type: PipelineType = PipelineType.AUTO,
        options: Optional[ConversionOptions] = None,
        job_id: Optional[str] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Streams progressive Markdown chunks and WebSocket-compatible status events.
        """
        opts = options or ConversionOptions()
        jid = job_id or str(uuid.uuid4())

        # Yield Initial Ingestion Frame
        yield StreamChunk(
            event="status",
            job_id=jid,
            stage="pipeline_dispatch",
            progress=5,
            message="Initializing multimodal conversion pipeline..."
        )

        try:
            resolved_pipeline = pipeline_type
            if resolved_pipeline == PipelineType.AUTO:
                resolved_pipeline = detect_pipeline_type(file_path)
        except Exception as e:
            code = getattr(e, "code", "INVALID_INPUT")
            yield StreamChunk(
                event="error",
                job_id=jid,
                code=code,
                message=str(e),
                recoverable=False
            )
            return

        if resolved_pipeline == PipelineType.VISION_OCR:
            async for chunk in self.vision_engine.convert_stream(file_path, opts, job_id=jid):
                yield chunk

        elif resolved_pipeline == PipelineType.VOICE_STT:
            async for chunk in self.voice_engine.convert_stream(file_path, opts, job_id=jid):
                yield chunk

        elif resolved_pipeline == PipelineType.TEXT_NORMALIZE:
            yield StreamChunk(
                event="status",
                job_id=jid,
                stage="text_normalization",
                progress=30,
                message="Normalizing HTML and structuring document tables..."
            )
            try:
                raw_text = file_path.read_text("utf-8", "replace")
                result = self.run_text_normalize(raw_text, opts, job_id=jid)

                paragraphs = [p + "\n\n" for p in result.markdown.split("\n\n") if p.strip()]
                for idx, para in enumerate(paragraphs):
                    yield StreamChunk(
                        event="chunk",
                        job_id=jid,
                        delta=para,
                        index=idx
                    )

                yield StreamChunk(
                    event="complete",
                    job_id=jid,
                    markdown=result.markdown,
                    metadata=result.metadata
                )
            except Exception as e:
                code = getattr(e, "code", "TEXT_NORMALIZE_ERROR")
                yield StreamChunk(
                    event="error",
                    job_id=jid,
                    code=code,
                    message=str(e),
                    recoverable=False
                )


# Global singleton runner instance
_default_runner = PipelineRunner()


async def run_pipeline(
    file_path: Path,
    pipeline_type: PipelineType = PipelineType.AUTO,
    options: Optional[ConversionOptions] = None,
    job_id: Optional[str] = None
) -> PipelineResult:
    """Module-level async execution matching interface contract."""
    return await _default_runner.run_pipeline(
        file_path,
        pipeline_type=pipeline_type,
        options=options,
        job_id=job_id
    )


async def stream_pipeline(
    file_path: Path,
    pipeline_type: PipelineType = PipelineType.AUTO,
    options: Optional[ConversionOptions] = None,
    job_id: Optional[str] = None
) -> AsyncIterator[StreamChunk]:
    """Module-level async streaming matching interface contract."""
    async for chunk in _default_runner.stream_pipeline(
        file_path,
        pipeline_type=pipeline_type,
        options=options,
        job_id=job_id
    ):
        yield chunk
