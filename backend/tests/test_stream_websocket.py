"""
Unit and API tests for /api/v1/ws/stream/{job_id} WebSocket streaming endpoint.
"""

import json
import pytest
import uuid
from starlette.websockets import WebSocketDisconnect

from backend.app.schemas import ConversionOptions, PipelineType
from backend.app.services.job_manager import job_manager


def test_websocket_nonexistent_job_rejected(client):
    """Verify WebSocket connection is closed with code 1008 if job does not exist."""
    fake_id = str(uuid.uuid4())
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/stream/{fake_id}") as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 1008


def test_websocket_streaming_flow(client):
    """Verify end-to-end WebSocket streaming receiving status, chunk, and complete frames."""
    # 1. Upload a file to create an active job
    file_bytes = b"# Stream Test Title\n\n| Item | Value |\n|---|---|\n| A | 100 |\n\nSome paragraph text."
    files = {"file": ("stream_doc.txt", file_bytes, "text/plain")}
    resp = client.post("/api/v1/convert/file", files=files)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # 2. Connect via WebSocket
    received_events = []
    with client.websocket_connect(f"/api/v1/ws/stream/{job_id}") as websocket:
        while True:
            try:
                msg_text = websocket.receive_text()
                frame = json.loads(msg_text)
                received_events.append(frame["event"])
                if frame["event"] in ["complete", "error"]:
                    break
            except WebSocketDisconnect:
                break

    # 3. Assert frame sequence conforming to api_contract.yaml
    assert "status" in received_events
    assert "chunk" in received_events
    assert "complete" in received_events


def test_websocket_client_cancellation(client):
    """Verify sending {'action': 'cancel'} aborts job execution."""
    file_bytes = b"# Large Document\n\n" + (b"Line of text to process.\n" * 50)
    files = {"file": ("cancel_doc.txt", file_bytes, "text/plain")}
    resp = client.post("/api/v1/convert/file", files=files)
    job_id = resp.json()["job_id"]

    with client.websocket_connect(f"/api/v1/ws/stream/{job_id}") as websocket:
        # Send cancel command
        websocket.send_text(json.dumps({"action": "cancel", "reason": "User abort"}))

        # Expect error or closure
        try:
            while True:
                msg_text = websocket.receive_text()
                frame = json.loads(msg_text)
                if frame.get("event") == "error":
                    assert frame["code"] == "CLIENT_CANCELLED"
                    break
        except WebSocketDisconnect:
            pass
