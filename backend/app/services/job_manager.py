"""
DTAMarkdown Studio - Job Manager Service.
Handles bounded asynchronous concurrency (asyncio.Semaphore(4)),
thread-safe job lifecycle state registry, event queue distribution,
and resilient detached background execution.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib
import logging
from pathlib import Path
import sys
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Set
import uuid

# Ensure ai-pipelines is in sys.path
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_AI_PIPELINES_DIR = _WORKSPACE_ROOT / "ai-pipelines"
if _AI_PIPELINES_DIR.exists() and str(_AI_PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINES_DIR))

from pipeline_runner import stream_pipeline, run_pipeline
from schemas import (
    PipelineType as AIPipelineType,
    ConversionOptions as AIConversionOptions,
    StreamChunk as AIStreamChunk,
)
from text_engine import TextNormalizer, TOCGenerator, TagExtractor

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
    WebSocketChunkFrame,
    WebSocketCompleteFrame,
    WebSocketErrorFrame,
    WebSocketStatusFrame,
    utc_now_iso,
)

logger = logging.getLogger("dtamarkdown.job_manager")


def _to_ai_options(opts: ConversionOptions) -> AIConversionOptions:
    """Map backend ConversionOptions schema to ai-pipelines ConversionOptions."""
    engine_val = opts.preferred_engine
    if hasattr(engine_val, "value"):
        engine_val = engine_val.value
    return AIConversionOptions(
        extract_tables=opts.extract_tables,
        extract_math=opts.extract_math,
        generate_toc=opts.generate_toc,
        extract_tags=opts.extract_tags,
        timestamp_silence_threshold=opts.timestamp_silence_threshold,
        preferred_engine=str(engine_val),
    )


def _to_ai_pipeline(ptype: PipelineType) -> AIPipelineType:
    """Map backend PipelineType enum to ai-pipelines PipelineType enum."""
    val = ptype.value if hasattr(ptype, "value") else str(ptype)
    return AIPipelineType(val)



@dataclass
class JobEntry:
    """Internal representation of a processing job."""
    job_id: str
    status: JobStatus
    pipeline: PipelineType
    options: ConversionOptions
    created_at: str = field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None
    progress: int = 0
    file_path: Optional[Path] = None
    raw_text: Optional[str] = None
    result: Optional[ConversionResult] = None
    error: Optional[ErrorResponse] = None
    accumulated_markdown: str = ""
    chunk_index: int = 0

    # Synchronization & Streaming
    subscribers: Set[asyncio.Queue] = field(default_factory=set)
    history_frames: List[Dict[str, Any]] = field(default_factory=list)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    worker_task: Optional[asyncio.Task] = None
    detached_at: Optional[float] = None
    detached_timeout_task: Optional[asyncio.Task] = None

    def to_detail_response(self) -> JobDetailResponse:
        """Convert entry into OpenAPI JobDetailResponse."""
        return JobDetailResponse(
            job_id=self.job_id,
            status=self.status,
            pipeline=self.pipeline,
            progress=self.progress,
            created_at=self.created_at,
            completed_at=self.completed_at,
            result=self.result,
            error=self.error,
        )


class JobManager:
    """
    Central in-memory job coordinator.
    Enforces concurrency limits and manages real-time event broadcasting.
    """

    def __init__(self, max_concurrent_jobs: Optional[int] = None):
        self.max_concurrent_jobs = max_concurrent_jobs or settings.MAX_CONCURRENT_JOBS
        self._semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
        self._jobs: Dict[str, JobEntry] = {}
        self._lock = asyncio.Lock()
        self._active_worker_count = 0

    @property
    def active_jobs_count(self) -> int:
        """Return count of active running jobs."""
        return self._active_worker_count

    async def create_job(
        self,
        pipeline_type: PipelineType,
        options: Optional[ConversionOptions] = None,
        file_path: Optional[Path] = None,
        raw_text: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> JobEntry:
        """Create and register a new job in QUEUED state."""
        jid = job_id or str(uuid.uuid4())
        opts = options or ConversionOptions()

        entry = JobEntry(
            job_id=jid,
            status=JobStatus.QUEUED,
            pipeline=pipeline_type,
            options=opts,
            file_path=file_path,
            raw_text=raw_text,
        )

        async with self._lock:
            self._jobs[jid] = entry

        logger.info("Created job %s [pipeline=%s, status=QUEUED]", jid, pipeline_type.value)
        return entry

    async def get_job(self, job_id: str) -> Optional[JobDetailResponse]:
        """Retrieve job details by id."""
        async with self._lock:
            entry = self._jobs.get(job_id)
            if not entry:
                return None
            return entry.to_detail_response()

    async def get_entry(self, job_id: str) -> Optional[JobEntry]:
        """Internal helper to retrieve raw JobEntry."""
        async with self._lock:
            return self._jobs.get(job_id)

    def submit_job(self, job_id: str):
        """Schedule background worker execution for the job."""
        entry = self._jobs.get(job_id)
        if entry and not entry.worker_task:
            entry.worker_task = asyncio.create_task(self._run_job_worker(job_id))

    async def subscribe(self, job_id: str) -> Optional[asyncio.Queue]:
        """
        Subscribe a WebSocket client to real-time events for this job.
        Replays prior frames (catch-up) so reconnecting clients do not miss data.
        """
        async with self._lock:
            entry = self._jobs.get(job_id)
            if not entry:
                return None

            queue: asyncio.Queue = asyncio.Queue()
            # Catch-up: replay historical frames
            for frame in entry.history_frames:
                await queue.put(frame)

            entry.subscribers.add(queue)

            # If client was disconnected and reconnects, cancel detached timeout
            if entry.detached_timeout_task and not entry.detached_timeout_task.done():
                entry.detached_timeout_task.cancel()
                entry.detached_at = None
                logger.info("Job %s client reconnected; cancelled detached timeout", job_id)

            return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        """Unsubscribe a client queue."""
        async with self._lock:
            entry = self._jobs.get(job_id)
            if entry and queue in entry.subscribers:
                entry.subscribers.remove(queue)

    async def mark_disconnected(self, job_id: str):
        """
        Mark a job as disconnected. Initiates 60-second detached background execution.
        If job is still running and no reconnect occurs in 60s, signals cancel_event.
        """
        async with self._lock:
            entry = self._jobs.get(job_id)
            if not entry:
                return

            if entry.status in (JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.STREAMING):
                entry.detached_at = time.time()
                logger.info(
                    "Job %s client disconnected. Allowing %ds detached execution.",
                    job_id,
                    settings.DETACHED_GRACE_PERIOD_SECONDS
                )
                entry.detached_timeout_task = asyncio.create_task(
                    self._detached_timeout_watcher(job_id, settings.DETACHED_GRACE_PERIOD_SECONDS)
                )

    async def _detached_timeout_watcher(self, job_id: str, timeout_seconds: int):
        """Background task that aborts job if client does not reconnect within grace window."""
        try:
            await asyncio.sleep(timeout_seconds)
            async with self._lock:
                entry = self._jobs.get(job_id)
                if entry and len(entry.subscribers) == 0:
                    if entry.status in (JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.STREAMING):
                        logger.warning(
                            "Job %s detached grace period (%ds) expired with no reconnect. Aborting.",
                            job_id,
                            timeout_seconds
                        )
                        entry.cancel_event.set()
                        entry.status = JobStatus.CANCELLED
                        entry.completed_at = utc_now_iso()
                        entry.error = ErrorResponse(
                            code="CLIENT_DETACHED_TIMEOUT",
                            message=f"Execution cancelled after {timeout_seconds}s detached with no client reconnect.",
                        )
        except asyncio.CancelledError:
            pass

    async def cancel_job(self, job_id: str, reason: str = "Client cancelled"):
        """Explicitly cancel an active job."""
        async with self._lock:
            entry = self._jobs.get(job_id)
            if not entry:
                return

            entry.cancel_event.set()
            if entry.status in (JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.STREAMING):
                entry.status = JobStatus.CANCELLED
                entry.completed_at = utc_now_iso()
                entry.error = ErrorResponse(
                    code="CLIENT_CANCELLED",
                    message=reason,
                )
                err_frame = WebSocketErrorFrame(
                    job_id=job_id,
                    code="CLIENT_CANCELLED",
                    message=reason,
                    recoverable=False,
                ).model_dump()
                await self._broadcast(entry, err_frame)

        logger.info("Cancelled job %s: %s", job_id, reason)

    async def _broadcast(self, entry: JobEntry, frame: Dict[str, Any]):
        """Internal helper to broadcast a frame to all subscribers and append to history."""
        entry.history_frames.append(frame)
        dead_queues = []
        for q in entry.subscribers:
            try:
                await q.put(frame)
            except Exception:
                dead_queues.append(q)
        for dq in dead_queues:
            entry.subscribers.discard(dq)

    async def emit_status(self, entry: JobEntry, stage: str, progress: int, message: str):
        """Emit status frame update."""
        entry.progress = progress
        frame = WebSocketStatusFrame(
            job_id=entry.job_id,
            stage=stage,
            progress=progress,
            message=message,
        ).model_dump()
        await self._broadcast(entry, frame)

    async def emit_chunk(self, entry: JobEntry, delta: str):
        """Emit incremental markdown chunk frame."""
        frame = WebSocketChunkFrame(
            job_id=entry.job_id,
            delta=delta,
            index=entry.chunk_index,
        ).model_dump()
        entry.chunk_index += 1
        entry.accumulated_markdown += delta
        await self._broadcast(entry, frame)

    async def emit_complete(self, entry: JobEntry, markdown: str, metadata: Optional[ConversionMetadata] = None):
        """Emit completion frame."""
        entry.status = JobStatus.COMPLETED
        entry.completed_at = utc_now_iso()
        entry.progress = 100
        entry.accumulated_markdown = markdown

        meta = metadata or ConversionMetadata(
            word_count=len(markdown.split()),
            character_count=len(markdown),
            estimated_read_time=f"{max(1, len(markdown.split()) // 200)} min",
        )

        frame = WebSocketCompleteFrame(
            job_id=entry.job_id,
            markdown=markdown,
            metadata=meta,
        ).model_dump()
        await self._broadcast(entry, frame)

    async def emit_error(self, entry: JobEntry, code: str, message: str, recoverable: bool = False):
        """Emit error frame."""
        entry.status = JobStatus.FAILED
        entry.completed_at = utc_now_iso()
        entry.error = ErrorResponse(code=code, message=message)

        frame = WebSocketErrorFrame(
            job_id=entry.job_id,
            code=code,
            message=message,
            recoverable=recoverable,
        ).model_dump()
        await self._broadcast(entry, frame)

    async def _run_job_worker(self, job_id: str):
        """Background coroutine that acquires semaphore and executes conversion."""
        entry = self._jobs.get(job_id)
        if not entry:
            return

        start_time = time.time()
        logger.info("Job %s waiting for concurrency semaphore...", job_id)

        try:
            async with self._semaphore:
                self._active_worker_count += 1
                try:
                    if entry.cancel_event.is_set():
                        return

                    entry.status = JobStatus.PROCESSING
                    logger.info("Job %s acquired semaphore; beginning conversion.", job_id)

                    await self._execute_conversion_pipeline(entry)

                finally:
                    self._active_worker_count = max(0, self._active_worker_count - 1)

        except Exception as e:
            logger.exception("Unexpected exception in job worker for %s: %s", job_id, e)
            await self.emit_error(entry, code="INTERNAL_PIPELINE_ERROR", message=str(e))
        finally:
            duration_ms = (time.time() - start_time) * 1000
            if entry.status == JobStatus.COMPLETED and not entry.result:
                meta = ConversionMetadata(
                    word_count=len(entry.accumulated_markdown.split()),
                    character_count=len(entry.accumulated_markdown),
                    duration_ms=round(duration_ms, 2),
                )
                entry.result = ConversionResult(
                    job_id=entry.job_id,
                    success=True,
                    pipeline=entry.pipeline,
                    markdown=entry.accumulated_markdown,
                    metadata=meta,
                    warnings=[],
                    duration_ms=round(duration_ms, 2),
                )

    async def _execute_conversion_pipeline(self, entry: JobEntry):
        """
        Coordinates streaming chunk delivery to connected subscribers.
        Streams genuine multimodal conversion chunks using ai-pipelines runner.
        """
        # Step 1: Initial Status Frame
        await self.emit_status(
            entry,
            stage="initialization",
            progress=10,
            message="Validating input and preparing pipeline..."
        )
        await asyncio.sleep(0.05)

        if entry.cancel_event.is_set():
            return

        entry.status = JobStatus.STREAMING

        # If file_path is provided, stream directly from stream_pipeline
        if entry.file_path and entry.file_path.exists():
            try:
                ai_opts = _to_ai_options(entry.options)
                ai_pipeline = _to_ai_pipeline(entry.pipeline)

                async for chunk in stream_pipeline(
                    file_path=entry.file_path,
                    pipeline_type=ai_pipeline,
                    options=ai_opts,
                    job_id=entry.job_id,
                ):
                    if entry.cancel_event.is_set():
                        return
                    if chunk.event == "status":
                        await self.emit_status(entry, chunk.stage or "running", chunk.progress or 50, chunk.message or "")
                    elif chunk.event == "chunk":
                        await self.emit_chunk(entry, chunk.delta or "")
                    elif chunk.event == "complete":
                        meta = None
                        if chunk.metadata:
                            meta = ConversionMetadata(**chunk.metadata)
                        await self.emit_complete(entry, chunk.markdown or entry.accumulated_markdown, meta)
                        return
                    elif chunk.event == "error":
                        await self.emit_error(entry, chunk.code or "PIPELINE_ERROR", chunk.message or "Error")
                        return
                return
            except Exception as e:
                logger.error("stream_pipeline streaming error for job %s: %s", entry.job_id, e)
                await self.emit_error(entry, getattr(e, "code", "PIPELINE_ERROR"), str(e))
                return

        # Route by pipeline type for text or direct inputs
        if entry.pipeline == PipelineType.TEXT_NORMALIZE or entry.raw_text is not None:
            await self._process_text_pipeline(entry)
        elif entry.pipeline == PipelineType.VOICE_STT:
            await self._process_voice_pipeline(entry)
        else:
            await self._process_document_pipeline(entry)

    async def _process_text_pipeline(self, entry: JobEntry):
        """Process unstructured text or HTML input using TextNormalizer and TOCGenerator."""
        await self.emit_status(entry, stage="text_normalization", progress=30, message="Normalizing text structure...")
        await asyncio.sleep(0.05)

        raw = entry.raw_text or ""
        if entry.file_path and entry.file_path.exists():
            try:
                raw = entry.file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        normalizer = TextNormalizer()
        res = normalizer.normalize(
            raw,
            extract_tables=entry.options.extract_tables,
            extract_math=entry.options.extract_math,
        )
        if isinstance(res, tuple):
            markdown_out, _ = res
        else:
            markdown_out = res

        import re
        markdown_out = re.sub(r"\|\s*---\s*(\|\s*---\s*)+\|", lambda m: re.sub(r"\s+", "", m.group(0)), markdown_out)

        if entry.options.generate_toc:
            toc_str = TOCGenerator.generate_toc(markdown_out)
            if toc_str:
                markdown_out = TOCGenerator.inject_toc(markdown_out, toc_str)

        w_count, c_count = TagExtractor.calculate_word_and_char_count(markdown_out)
        read_time = TagExtractor.estimate_read_time(w_count)
        tags = TagExtractor.extract_tags(markdown_out) if entry.options.extract_tags else []

        if entry.options.extract_tags and w_count > 0:
            doc_title = TagExtractor.extract_document_title(markdown_out)
            fm = TagExtractor.generate_frontmatter(doc_title, tags, w_count, read_time)
            markdown_out = TagExtractor.inject_frontmatter(markdown_out, fm)

        # Stream out in chunks
        lines = markdown_out.splitlines(keepends=True)
        chunk_buf = ""
        total_lines = max(1, len(lines))

        for idx, line in enumerate(lines):
            if entry.cancel_event.is_set():
                return
            chunk_buf += line
            if len(chunk_buf) >= 120 or idx == len(lines) - 1:
                progress = 30 + int(60 * (idx + 1) / total_lines)
                await self.emit_chunk(entry, chunk_buf)
                chunk_buf = ""
                await asyncio.sleep(0.01)

        await self.emit_status(entry, stage="finalizing", progress=95, message="Finalizing text conversion...")
        await asyncio.sleep(0.02)

        meta = ConversionMetadata(
            word_count=w_count,
            character_count=c_count,
            estimated_read_time=read_time,
            engine_used="Text Normalizer Engine",
            tags=tags,
        )
        await self.emit_complete(entry, markdown_out, meta)

    async def _process_document_pipeline(self, entry: JobEntry):
        """Process document scans, PDFs, or images via VisionOCREngine."""
        if not entry.file_path or not entry.file_path.exists():
            await self.emit_error(entry, "FILE_NOT_FOUND", "No valid document file provided.")
            return

        try:
            ai_opts = _to_ai_options(entry.options)
            result = await run_pipeline(
                file_path=entry.file_path,
                pipeline_type=AIPipelineType.VISION_OCR,
                options=ai_opts,
                job_id=entry.job_id,
            )
            meta = ConversionMetadata(**result.metadata) if result.metadata else None
            await self.emit_complete(entry, result.markdown, meta)
        except Exception as e:
            logger.error("Vision OCR pipeline error for job %s: %s", entry.job_id, e)
            await self.emit_error(entry, getattr(e, "code", "OCR_FAILED"), str(e))

    async def _process_voice_pipeline(self, entry: JobEntry):
        """Process voice/audio transcription via VoiceSTTEngine."""
        if not entry.file_path or not entry.file_path.exists():
            await self.emit_error(entry, "FILE_NOT_FOUND", "No valid audio file provided.")
            return

        try:
            ai_opts = _to_ai_options(entry.options)
            result = await run_pipeline(
                file_path=entry.file_path,
                pipeline_type=AIPipelineType.VOICE_STT,
                options=ai_opts,
                job_id=entry.job_id,
            )
            meta = ConversionMetadata(**result.metadata) if result.metadata else None
            await self.emit_complete(entry, result.markdown, meta)
        except Exception as e:
            logger.error("Voice STT pipeline error for job %s: %s", entry.job_id, e)
            await self.emit_error(entry, getattr(e, "code", "STT_FAILED"), str(e))


job_manager = JobManager()
