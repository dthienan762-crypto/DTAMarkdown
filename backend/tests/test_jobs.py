"""
Unit and API tests for /api/v1/jobs/{job_id} endpoint.
"""

import pytest
import uuid


def test_get_job_not_found(client):
    """Verify HTTP 404 on nonexistent job UUID."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/jobs/{fake_id}")
    assert response.status_code == 404

    data = response.json()
    assert data["code"] == "JOB_NOT_FOUND"


def test_get_job_lifecycle(client):
    """Create a file conversion job and verify polling via GET /api/v1/jobs/{job_id}."""
    file_content = b"# Document for Polling\n\nSome paragraph text."
    files = {"file": ("polling_doc.txt", file_content, "text/plain")}
    post_resp = client.post("/api/v1/convert/file", files=files)
    assert post_resp.status_code == 202

    job_id = post_resp.json()["job_id"]

    # Poll job status
    get_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 200

    job_data = get_resp.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"] in ["QUEUED", "PROCESSING", "STREAMING", "COMPLETED"]
    assert job_data["pipeline"] == "text_normalize"
    assert "created_at" in job_data
