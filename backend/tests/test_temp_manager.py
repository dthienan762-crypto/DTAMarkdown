"""
Unit tests for ManagedTempFile and TempReaperService.
Adheres to Principle 3 (Deterministic Tempfile Lifecycle).
"""

import os
from pathlib import Path
import tempfile
import time
import pytest

from backend.app.services.temp_manager import (
    ManagedTempFile,
    TempReaperService,
    sanitize_filename,
)


def test_sanitize_filename_traversal():
    """Verify path traversal patterns are strictly stripped."""
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("safe_document.pdf") == "safe_document.pdf"
    assert sanitize_filename("messy spaces & (brackets).png") == "messy_spaces____brackets_.png"


def test_managed_temp_file_deterministic_cleanup():
    """Verify ManagedTempFile automatically unlinks file on context exit."""
    staged_file_path = None
    with ManagedTempFile(content_bytes=b"temporary bytes to test auto-unlink", filename="test.bin") as path:
        staged_file_path = path
        assert staged_file_path.exists()
        assert staged_file_path.read_bytes() == b"temporary bytes to test auto-unlink"

    # Must be unlinked after with-block exits
    assert not staged_file_path.exists()


def test_managed_temp_file_cleanup_on_exception():
    """Verify file is unlinked even when exception occurs inside context."""
    staged_file_path = None
    try:
        with ManagedTempFile(content_bytes=b"data before error", filename="err.bin") as path:
            staged_file_path = path
            assert staged_file_path.exists()
            raise RuntimeError("Simulated conversion failure")
    except RuntimeError:
        pass

    assert staged_file_path is not None
    assert not staged_file_path.exists()


def test_temp_reaper_startup_sweep():
    """Verify startup_sweep purges existing leftover files in staging."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        staging_dir = Path(tmp_dir)
        # Create dummy orphaned files
        (staging_dir / "orphan1.bin").write_text("old file 1")
        (staging_dir / "orphan2.bin").write_text("old file 2")
        sub_dir = staging_dir / "orphan_folder"
        sub_dir.mkdir()
        (sub_dir / "nested.bin").write_text("nested")

        assert len(list(staging_dir.iterdir())) == 3

        purged = TempReaperService.startup_sweep(staging_dir)
        assert purged == 3
        assert len(list(staging_dir.iterdir())) == 0


def test_temp_reaper_purge_expired_files():
    """Verify purge_expired_files deletes files older than max_age_seconds."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        staging_dir = Path(tmp_dir)
        old_file = staging_dir / "expired.bin"
        old_file.write_text("expired content")

        # Artificially set file modification time to 40 minutes ago
        past_time = time.time() - 2400
        os.utime(old_file, (past_time, past_time))

        new_file = staging_dir / "fresh.bin"
        new_file.write_text("fresh content")

        reaper = TempReaperService(staging_dir=staging_dir, max_age_seconds=1800)
        purged = reaper.purge_expired_files()

        assert purged == 1
        assert not old_file.exists()
        assert new_file.exists()
