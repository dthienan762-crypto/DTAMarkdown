"""
DTAMarkdown Studio - Temp File & Reaper Service.
Adheres strictly to Principle 3 (Zero Data Leakage & Deterministic Tempfile Lifecycle).
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Optional, Union
import uuid

from fastapi import HTTPException, UploadFile

from backend.app.config import settings

logger = logging.getLogger("dtamarkdown.temp_manager")


class PayloadTooLargeException(HTTPException):
    """Raised when uploaded file exceeds allowed payload size limits."""
    def __init__(self, detail: str = "Payload exceeds maximum allowed size."):
        super().__init__(status_code=413, detail=detail)


class EmptyFilePayloadException(HTTPException):
    """Raised when uploaded file contains 0 bytes."""
    def __init__(self, detail: str = "Uploaded file payload is empty."):
        super().__init__(status_code=400, detail=detail)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename against directory traversal and dangerous characters.
    Strips path separators, relative path markers, and special chars.
    """
    if not filename:
        return "upload.bin"
    # Extract only basename
    basename = Path(filename).name
    # Remove directory traversal patterns
    basename = basename.replace("..", "").replace("/", "").replace("\\", "")
    # Keep only alphanumeric, hyphen, underscore, dot
    sanitized = re.sub(r"[^\w.-]", "_", basename)
    return sanitized or "upload.bin"


def get_staging_dir() -> Path:
    """Return ensure and return the staging directory path."""
    staging = settings.STAGING_DIR
    staging.mkdir(parents=True, exist_ok=True)
    return staging


class ManagedTempFile:
    """
    Deterministic context manager for staged upload files.
    Ensures safe streaming write with size bounds checking,
    and guaranteed unlinking in a finally block.
    """

    def __init__(
        self,
        upload_file: Optional[UploadFile] = None,
        job_id: Optional[str] = None,
        max_bytes: Optional[int] = None,
        content_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ):
        self.upload_file = upload_file
        self.job_id = job_id or str(uuid.uuid4())
        self.max_bytes = max_bytes
        self.content_bytes = content_bytes
        self.filename = filename or (upload_file.filename if upload_file else "upload.bin")
        self.staged_path: Optional[Path] = None

    async def __aenter__(self) -> Path:
        staging_dir = get_staging_dir()
        clean_name = sanitize_filename(self.filename)
        timestamp_ms = int(time.time() * 1000)
        dest_filename = f"{self.job_id}_{timestamp_ms}_{clean_name}"
        self.staged_path = staging_dir / dest_filename

        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB buffer

        try:
            if self.content_bytes is not None:
                # Direct byte payload staging
                total_bytes = len(self.content_bytes)
                if total_bytes == 0:
                    raise EmptyFilePayloadException("Uploaded file contains 0 bytes.")
                if self.max_bytes and total_bytes > self.max_bytes:
                    raise PayloadTooLargeException(
                        f"File size ({total_bytes} bytes) exceeds limit ({self.max_bytes} bytes)."
                    )
                with open(self.staged_path, "wb") as f:
                    f.write(self.content_bytes)

            elif self.upload_file is not None:
                # Stream write from UploadFile
                with open(self.staged_path, "wb") as f:
                    while True:
                        chunk = await self.upload_file.read(chunk_size)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if self.max_bytes and total_bytes > self.max_bytes:
                            raise PayloadTooLargeException(
                                f"Uploaded file exceeds maximum allowed limit of {self.max_bytes} bytes."
                            )
                        f.write(chunk)

                if total_bytes == 0:
                    raise EmptyFilePayloadException("Uploaded file contains 0 bytes.")
            else:
                # Placeholder file
                self.staged_path.touch()

            logger.info("Staged %d bytes for job %s at %s", total_bytes, self.job_id, self.staged_path)
            return self.staged_path

        except Exception:
            self._cleanup()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def __enter__(self) -> Path:
        """Synchronous context manager variant."""
        staging_dir = get_staging_dir()
        clean_name = sanitize_filename(self.filename)
        timestamp_ms = int(time.time() * 1000)
        dest_filename = f"{self.job_id}_{timestamp_ms}_{clean_name}"
        self.staged_path = staging_dir / dest_filename

        try:
            if self.content_bytes is not None:
                total_bytes = len(self.content_bytes)
                if total_bytes == 0:
                    raise EmptyFilePayloadException("Uploaded file contains 0 bytes.")
                if self.max_bytes and total_bytes > self.max_bytes:
                    raise PayloadTooLargeException(
                        f"File size ({total_bytes} bytes) exceeds limit ({self.max_bytes} bytes)."
                    )
                with open(self.staged_path, "wb") as f:
                    f.write(self.content_bytes)
            else:
                self.staged_path.touch()
            return self.staged_path
        except Exception:
            self._cleanup()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def _cleanup(self):
        """Deterministically unlink the staged file."""
        if self.staged_path and self.staged_path.exists():
            try:
                self.staged_path.unlink(missing_ok=True)
                logger.info("Unlinked staged tempfile: %s", self.staged_path)
            except Exception as e:
                logger.warning("Failed to unlink %s: %s", self.staged_path, e)


class TempReaperService:
    """
    Autonomous background sweeper and startup staging cleaner.
    Guarantees 0% disk accumulation over long uptimes.
    """

    def __init__(self, staging_dir: Optional[Path] = None, interval_seconds: Optional[int] = None, max_age_seconds: Optional[int] = None):
        self.staging_dir = staging_dir or settings.STAGING_DIR
        self.interval_seconds = interval_seconds or settings.REAPER_INTERVAL_SECONDS
        self.max_age_seconds = max_age_seconds or settings.REAPER_MAX_AGE_SECONDS
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

    @classmethod
    def startup_sweep(cls, staging_dir: Optional[Path] = None) -> int:
        """
        Synchronous startup staging sweep invoked during FastAPI lifespan boot.
        Purges leftover orphaned files from prior crashes.
        Returns the count of purged files.
        """
        target_dir = staging_dir or settings.STAGING_DIR
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            return 0

        purged_count = 0
        logger.info("Executing startup staging sweep on %s...", target_dir)

        try:
            for item in target_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink(missing_ok=True)
                        purged_count += 1
                    except Exception as e:
                        logger.warning("Startup sweep: could not unlink %s: %s", item, e)
                elif item.is_dir():
                    try:
                        shutil.rmtree(item, ignore_errors=True)
                        purged_count += 1
                    except Exception as e:
                        logger.warning("Startup sweep: could not remove dir %s: %s", item, e)
        except Exception as e:
            logger.error("Error during startup staging sweep: %s", e)

        logger.info("Startup staging sweep complete. Purged %d orphaned files/dirs.", purged_count)
        return purged_count

    def purge_expired_files(self) -> int:
        """
        Scan staging directory and purge files whose mtime exceeds max_age_seconds.
        Returns the count of purged files.
        """
        if not self.staging_dir.exists():
            return 0

        now = time.time()
        purged = 0

        for item in self.staging_dir.iterdir():
            if item.is_file():
                try:
                    stat = item.stat()
                    age = now - stat.st_mtime
                    if age > self.max_age_seconds:
                        item.unlink(missing_ok=True)
                        purged += 1
                        logger.info("Reaper purged expired file: %s (age %.1fs)", item.name, age)
                except Exception as e:
                    logger.warning("Reaper could not check/unlink %s: %s", item, e)

        return purged

    async def _loop(self):
        """Periodic reaper loop."""
        logger.info(
            "TempReaperService started (interval=%ds, max_age=%ds).",
            self.interval_seconds,
            self.max_age_seconds
        )
        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                purged = self.purge_expired_files()
                if purged > 0:
                    logger.info("Periodic sweep purged %d expired files.", purged)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in TempReaperService loop: %s", e)

    def start(self):
        """Start the background reaper task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        """Stop the background reaper task."""
        if self._running:
            self._running = False
            if self._task and not self._task.done():
                self._task.cancel()
            logger.info("TempReaperService stopped.")
