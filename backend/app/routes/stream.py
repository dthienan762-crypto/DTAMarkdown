"""
DTAMarkdown Studio - WebSocket Streaming Route.
Endpoint: /api/v1/ws/stream/{job_id}
Conforms to docs/specs/api_contract.yaml and docs/specs/core_principles.md.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, WebSocket

from backend.app.websocket.connection_manager import connection_manager

logger = logging.getLogger("dtamarkdown.routes.stream")

router = APIRouter(prefix="/api/v1/ws", tags=["streaming"])


@router.websocket("/stream/{job_id}")
async def stream_job_websocket(websocket: WebSocket, job_id: str):
    """
    Full-duplex WebSocket streaming endpoint.
    Emits structured JSON frames:
    - WebSocketStatusFrame (event: "status")
    - WebSocketChunkFrame (event: "chunk")
    - WebSocketCompleteFrame (event: "complete")
    - WebSocketErrorFrame (event: "error")
    """
    await connection_manager.handle_stream(websocket, job_id)
