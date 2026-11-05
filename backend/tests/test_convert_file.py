"""
Unit and API tests for /api/v1/convert/file endpoint.
"""

import io
import pytest
from unittest.mock import patch
from backend.app.config import settings


def test_convert_file_valid_upload(client):
    """Test valid file upload returns 202 Accepted with job ID and stream URL."""
    file_content = b"# Sample Document\n\nSome text content."
    files = {"file": ("document.txt", file_content, "text/plain")}
    data = {
        "pipeline_type": "text_normalize",
        "options_json": '{"extract_tables": true, "generate_toc": false}',
    }
    response = client.post("/api/v1/convert/file", files=files, data=data)
    assert response.status_code == 202

    resp_data = response.json()
    assert "job_id" in resp_data
    assert resp_data["status"] == "QUEUED"
    assert resp_data["pipeline"] == "text_normalize"
    assert "stream_url" in resp_data
    assert resp_data["stream_url"].startswith("/api/v1/ws/stream/")


def test_convert_file_empty_file_rejected(client):
    """Verify HTTP 400 Bad Request with code EMPTY_FILE_PAYLOAD on 0-byte file."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    response = client.post("/api/v1/convert/file", files=files)
    assert response.status_code == 400

    resp_data = response.json()
    assert resp_data["code"] == "EMPTY_FILE_PAYLOAD"


def test_convert_file_malformed_options_json(client):
    """Verify HTTP 400 Bad Request with code MALFORMED_OPTIONS_JSON on invalid JSON."""
    files = {"file": ("test.png", b"\x89PNG\r\n\x1a\nfakeimagebytes", "image/png")}
    data = {"options_json": "{broken-json-options"}
    response = client.post("/api/v1/convert/file", files=files, data=data)
    assert response.status_code == 400

    resp_data = response.json()
    assert resp_data["code"] == "MALFORMED_OPTIONS_JSON"


def test_convert_file_document_size_exceeded(client):
    """Verify HTTP 413 Payload Too Large when document exceeds limit (tested via lowered threshold)."""
    # Temporarily set max doc size to 1KB to test 413 without allocating 50MB in test
    with patch.object(settings, "MAX_DOCUMENT_SIZE_BYTES", 1024):
        large_content = b"X" * 2048  # 2KB > 1KB
        files = {"file": ("document.pdf", large_content, "application/pdf")}
        response = client.post("/api/v1/convert/file", files=files)
        assert response.status_code == 413

        resp_data = response.json()
        assert resp_data["code"] == "PAYLOAD_TOO_LARGE"


def test_convert_file_audio_pipeline_inference(client):
    """Verify audio file MIME/extension correctly infers voice_stt pipeline."""
    files = {"file": ("recording.wav", b"RIFFfakeaudio16bitpcmwav", "audio/wav")}
    response = client.post("/api/v1/convert/file", files=files)
    assert response.status_code == 202

    resp_data = response.json()
    assert resp_data["pipeline"] == "voice_stt"


def test_convert_file_audio_size_exceeded(client):
    """Verify HTTP 413 Payload Too Large when audio exceeds limit."""
    with patch.object(settings, "MAX_AUDIO_SIZE_BYTES", 2048):
        large_audio = b"W" * 4096
        files = {"file": ("speech.wav", large_audio, "audio/wav")}
        response = client.post("/api/v1/convert/file", files=files)
        assert response.status_code == 413

        resp_data = response.json()
        assert resp_data["code"] == "PAYLOAD_TOO_LARGE"
