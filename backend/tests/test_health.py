"""
Unit and API tests for /api/v1/health endpoint.
"""

import pytest


def test_health_endpoint(client):
    """Verify /api/v1/health returns 200 with complete telemetry."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["version"] == "1.0.0"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0

    engines = data["engines_available"]
    assert engines["pymupdf_fast"] is True
    assert "gemini_vision" in engines
    assert "rapidocr_onnx" in engines
    assert "speech_recognition" in engines
    assert isinstance(data["active_jobs"], int)
