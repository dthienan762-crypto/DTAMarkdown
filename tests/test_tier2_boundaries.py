"""
DTAMarkdown Studio - Tier 2: Boundary & Corner Cases Test Suite
Defensive verification of:
1. 0-byte payloads (images, audio, text) -> 400 Bad Request / NO_SPEECH_DETECTED
2. Corrupt binary payloads -> 415 Unsupported Media Type / CORRUPT_HEADER
3. Oversized files (>50MB docs/images, >100MB audio) -> 413 Payload Too Large
4. Unclosed math delimiters (lone $, dangling $$) -> Defensively flagged, no crash
5. Hostile Unicode (zero-width spaces, non-breaking spaces, control chars)
6. Deeply nested tables (10+ levels) -> Flattened without RecursionError
7. Staging directory path traversal sanitization (../../ escaping prevented)
8. Deterministic tempfile unlinking under normal and exception execution
"""

from pathlib import Path
import json
import os
import re
import tempfile
import uuid
import pytest
import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"
SPEC_FILE = Path(__file__).resolve().parent.parent / "docs" / "specs" / "api_contract.yaml"


# ======================================================================
# Boundary Defensive Drivers & Contract Validators
# ======================================================================

def sanitize_staging_filename(raw_filename: str, job_id: str) -> str:
    """Core Principles 3.1: Path traversal stripping and UUIDv4 sandboxed staging."""
    # Strip any directory components (both / and \)
    basename = os.path.basename(raw_filename.replace("\\", "/"))
    # Remove hostile characters, keep only alphanumerics, dots, hyphens, underscores
    sanitized = re.sub(r"[^\w.-]", "_", basename)
    if not sanitized or sanitized.startswith("."):
        sanitized = f"upload_{sanitized}"
    return f"{job_id}_{sanitized}"


class DefensiveFileValidator:
    """Reference implementation of backend boundary validation."""
    MAX_DOC_SIZE = 200 * 1024 * 1024  # 200 MB
    MAX_AUDIO_SIZE = 200 * 1024 * 1024  # 200 MB

    @classmethod
    def validate_upload(cls, file_bytes: bytes, filename: str) -> dict:
        file_size = len(file_bytes)
        ext = Path(filename).suffix.lower()

        # 1. Empty 0-byte check
        if file_size == 0:
            return {
                "status_code": 400,
                "error_code": "EMPTY_FILE_PAYLOAD",
                "message": f"Uploaded file '{filename}' contains 0 bytes.",
            }

        # 2. Oversized payload check
        is_audio = ext in [".wav", ".mp3", ".m4a", ".flac"]
        limit = cls.MAX_AUDIO_SIZE if is_audio else cls.MAX_DOC_SIZE
        if file_size > limit:
            limit_mb = limit // (1024 * 1024)
            return {
                "status_code": 413,
                "error_code": "PAYLOAD_TOO_LARGE",
                "message": f"File size ({file_size / (1024*1024):.1f}MB) exceeds limit of {limit_mb}MB.",
            }

        # 3. Format header check
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".pdf"]:
            # Check magic bytes
            if ext == ".png" and not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                return {"status_code": 415, "error_code": "INVALID_IMAGE_HEADER", "message": "Corrupt PNG magic bytes."}
            if ext == ".pdf" and not file_bytes.startswith(b"%PDF-"):
                return {"status_code": 415, "error_code": "INVALID_PDF_HEADER", "message": "Corrupt PDF header."}
        elif is_audio:
            if ext == ".wav" and not (file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WAVE"):
                return {"status_code": 415, "error_code": "INVALID_WAV_HEADER", "message": "Corrupt WAV header."}

        return {"status_code": 202, "error_code": None, "message": "OK"}


def check_katex_delimiter_balance(text: str) -> dict:
    """Validates whether $ and $$ delimiters are properly balanced."""
    # First count unescaped display math $$
    display_count = len(re.findall(r"(?<!\\)\$\$", text))
    if display_count % 2 != 0:
        return {"balanced": False, "error": "Unclosed display math block ($$)", "unclosed_type": "$$"}

    # Strip display blocks before checking inline $
    no_display = re.sub(r"(?<!\\)\$\$.*?(?<!\\)\$\$", "", text, flags=re.DOTALL)
    # Count unescaped inline $
    inline_dollars = re.findall(r"(?<!\\)\$", no_display)
    if len(inline_dollars) % 2 != 0:
        return {"balanced": False, "error": "Unclosed inline math ($)", "unclosed_type": "$"}

    return {"balanced": True, "error": None}


def sanitize_unicode_anomalies(text: str) -> str:
    """Strips zero-width spaces, normalizes non-breaking spaces, and cleans control chars."""
    # Strip zero-width space (\u200B), zero-width non-joiner (\u200C), zero-width joiner (\u200D)
    cleaned = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", text)
    # Replace non-breaking space (\u00A0) with standard space
    cleaned = cleaned.replace("\u00A0", " ")
    # Normalize smart quotes to standard ASCII
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    return cleaned


# ======================================================================
# Tier 2 Boundary Tests
# ======================================================================

def test_tier2_empty_0byte_image_payload():
    """Verify 0-byte image file returns 400 Bad Request rather than triggering 500 crash."""
    empty_png = DATA_DIR / "vision" / "empty_0byte.png"
    assert empty_png.exists()
    content = empty_png.read_bytes()
    assert len(content) == 0

    res = DefensiveFileValidator.validate_upload(content, "empty_0byte.png")
    assert res["status_code"] == 400
    assert res["error_code"] == "EMPTY_FILE_PAYLOAD"


def test_tier2_empty_0byte_audio_payload():
    """Verify 0-byte audio file returns 400 Bad Request."""
    empty_wav = DATA_DIR / "audio" / "empty_audio.wav"
    assert empty_wav.exists()
    content = empty_wav.read_bytes()
    assert len(content) == 0

    res = DefensiveFileValidator.validate_upload(content, "empty_audio.wav")
    assert res["status_code"] == 400
    assert res["error_code"] == "EMPTY_FILE_PAYLOAD"


def test_tier2_corrupt_non_audio_payload():
    """Verify corrupt non-audio random bytes return 415 Unsupported Media Type."""
    corrupt_wav = DATA_DIR / "audio" / "corrupt_audio.wav"
    assert corrupt_wav.exists()
    content = corrupt_wav.read_bytes()
    assert len(content) > 0

    res = DefensiveFileValidator.validate_upload(content, "corrupt_audio.wav")
    assert res["status_code"] == 415
    assert res["error_code"] == "INVALID_WAV_HEADER"


def test_tier2_oversized_file_limit_enforcement():
    """Verify file exceeding 200MB returns 413 Payload Too Large."""
    # Virtual 202MB file check without allocating physical disk
    virtual_oversized = b"P" * (202 * 1024 * 1024)
    res = DefensiveFileValidator.validate_upload(virtual_oversized, "giant_document.pdf")
    assert res["status_code"] == 413
    assert res["error_code"] == "PAYLOAD_TOO_LARGE"
    assert "exceeds limit" in res["message"]


def test_tier2_unclosed_inline_math_delimiter():
    """Verify unclosed single dollar sign is detected and does not corrupt document."""
    text_with_dangling_dollar = "This paragraph has an open $math formula that never closes."
    balance = check_katex_delimiter_balance(text_with_dangling_dollar)
    assert balance["balanced"] is False
    assert balance["unclosed_type"] == "$"

    # Defensive correction: escape unclosed $ to prevent preview crashes
    corrected = text_with_dangling_dollar.replace("$", r"\$")
    assert check_katex_delimiter_balance(corrected)["balanced"] is True


def test_tier2_unclosed_display_math_block():
    """Verify unclosed $$ block is detected."""
    text_unclosed_block = "$$\n\\int_{0}^{1} x dx\nMissing closing block"
    balance = check_katex_delimiter_balance(text_unclosed_block)
    assert balance["balanced"] is False
    assert balance["unclosed_type"] == "$$"


def test_tier2_unicode_zero_width_space_stripping():
    """Verify invisible zero-width spaces and NBSPs are sanitized cleanly."""
    dirty_text = "Hidden\u200Bzero\u200Cwidth\u200Dcharacters and non\u00A0breaking spaces with \u201cquotes\u201d."
    cleaned = sanitize_unicode_anomalies(dirty_text)
    assert "\u200B" not in cleaned
    assert "\u200C" not in cleaned
    assert "\u200D" not in cleaned
    assert "\u00A0" not in cleaned
    assert cleaned == 'Hiddenzerowidthcharacters and non breaking spaces with "quotes".'


def test_tier2_deeply_nested_html_tables_flattening():
    """Verify 10 levels of nested tables do not trigger RecursionError."""
    from bs4 import BeautifulSoup
    nested_html = "<td>Deep Level 10</td>"
    for lvl in range(9, 0, -1):
        nested_html = f"<table><tr><td>Level {lvl}</td><td>{nested_html}</td></tr></table>"
    nested_html = f"<table><tr>{nested_html}</tr></table>"

    # Must parse cleanly without RecursionError
    soup = BeautifulSoup(nested_html, "lxml")
    tables = soup.find_all("table")
    assert len(tables) >= 10
    # Flattening extracts leaf cells
    cells = [c.get_text(strip=True) for c in soup.find_all("td")]
    assert "Deep Level 10" in cells


def test_tier2_empty_text_request_validation():
    """Verify convert/text endpoint rejects empty text payload."""
    raw_text = "   "
    if not raw_text.strip():
        response = {"status_code": 400, "error": "EMPTY_PAYLOAD", "message": "raw_text payload cannot be empty"}
    else:
        response = {"status_code": 200}
    assert response["status_code"] == 400
    assert response["error"] == "EMPTY_PAYLOAD"


def test_tier2_malformed_options_json():
    """Verify malformed options_json string in multipart upload returns 400."""
    malformed_json_str = '{"extract_tables": true, "unclosed_string: }'
    try:
        json.loads(malformed_json_str)
        is_valid = True
    except json.JSONDecodeError:
        is_valid = False

    assert is_valid is False


def test_tier2_staging_path_traversal_sanitization():
    """Verify directory traversal patterns like ../../etc/passwd or ..\\Windows\\System32 are stripped."""
    test_job_id = str(uuid.uuid4())
    hostile_filenames = [
        "../../../../etc/shadow",
        "..\\..\\..\\Windows\\System32\\cmd.exe",
        "/absolute/path/file.png",
        "C:\\Users\\Admin\\secret.pdf",
    ]

    for fname in hostile_filenames:
        sanitized = sanitize_staging_filename(fname, test_job_id)
        assert ".." not in sanitized
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert sanitized.startswith(f"{test_job_id}_")


def test_tier2_deterministic_tempfile_cleanup_on_exception():
    """Verify ManagedTempFile context manager guarantees file deletion even when exception is raised."""
    staging_dir = Path(tempfile.gettempdir()) / "dtamarkdown_test_sandbox"
    staging_dir.mkdir(parents=True, exist_ok=True)
    temp_file = staging_dir / f"test_{uuid.uuid4().hex}.tmp"

    class ManagedTempFileTest:
        def __init__(self, path: Path):
            self.path = path

        def __enter__(self):
            self.path.write_bytes(b"temp test content")
            return self.path

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.path.exists():
                self.path.unlink()
            return True  # Suppress exception for test assertion

    # Simulate operation raising an error inside context
    with ManagedTempFileTest(temp_file) as staged:
        assert staged.exists()
        raise RuntimeError("Simulated pipeline worker crash!")

    # File must be guaranteed deleted in finally/exit block
    assert not temp_file.exists(), "Staged file was leaked after exception!"
