"""
DTAMarkdown Studio - WebSocket Connection Manager.
Handles bidirectional streaming, client subscription lifecycle,
structured frame transmission, and standardized close codes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

from backend.app.schemas import JobStatus
from backend.app.services.job_manager import job_manager

logger = logging.getLogger("dtamarkdown.websocket")

# Standardized WebSocket Close Codes
WS_CLOSE_NORMAL = 1000
WS_CLOSE_INVALID_JOB = 1008
WS_CLOSE_INTERNAL_ERROR = 1011
WS_CLOSE_CLIENT_CANCELLED = 4499


class ConnectionManager:
    """Manages WebSocket client connections and frame streaming."""

    async def handle_stream(self, websocket: WebSocket, job_id: str):
        """
        Handle the full lifecycle of a streaming WebSocket connection.
        """
        # Validate job existence
        job = await job_manager.get_job(job_id)
        if not job:
            logger.warning("WS connection rejected: Job %s not found.", job_id)
            await websocket.accept()
            await websocket.close(code=WS_CLOSE_INVALID_JOB, reason="Job not found or expired")
            return

        await websocket.accept()
        logger.info("WS connection established for job %s.", job_id)

        queue = await job_manager.subscribe(job_id)
        if not queue:
            await websocket.close(code=WS_CLOSE_INVALID_JOB, reason="Could not subscribe to job")
            return

        # Start two concurrent tasks: receiver (listen for client cancel) and sender (push frames)
        sender_task = asyncio.create_task(self._sender_loop(websocket, job_id, queue))
        receiver_task = asyncio.create_task(self._receiver_loop(websocket, job_id))

        try:
            done, pending = await asyncio.wait(
                [sender_task, receiver_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
        except WebSocketDisconnect:
            logger.info("WS client disconnected for job %s.", job_id)
        except Exception as e:
            logger.warning("WS stream exception for job %s: %s", job_id, e)
        finally:
            await job_manager.unsubscribe(job_id, queue)
            await job_manager.mark_disconnected(job_id)
            logger.info("WS connection cleaned up for job %s.", job_id)

    async def _sender_loop(self, websocket: WebSocket, job_id: str, queue: asyncio.Queue):
        """Pushes structured JSON frames from the job manager queue to the WebSocket client."""
        try:
            while True:
                frame: Dict[str, Any] = await queue.get()
                event = frame.get("event")

                # Send structured JSON frame
                await websocket.send_text(json.dumps(frame))
                queue.task_done()

                if event == "complete":
                    logger.info("Sent complete frame for job %s. Closing cleanly.", job_id)
                    await asyncio.sleep(0.05)
                    await websocket.close(code=WS_CLOSE_NORMAL, reason="Conversion complete")
                    break
                elif event == "error":
                    code = frame.get("code", "")
                    close_code = WS_CLOSE_CLIENT_CANCELLED if code == "CLIENT_CANCELLED" else WS_CLOSE_INTERNAL_ERROR
                    logger.info("Sent error frame for job %s (code=%s). Closing with %d.", job_id, code, close_code)
                    await asyncio.sleep(0.05)
                    await websocket.close(code=close_code, reason=frame.get("message", "Error"))
                    break

        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.warning("Error in WS sender loop for job %s: %s", job_id, e)

    async def _receiver_loop(self, websocket: WebSocket, job_id: str):
        """Listens for client-sent control messages (such as cancel)."""
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    payload = json.loads(data)
                    action = payload.get("action")
                    if action == "cancel":
                        reason = payload.get("reason", "Cancelled by user")
                        logger.info("Received client cancel request for job %s: %s", job_id, reason)
                        await job_manager.cancel_job(job_id, reason=reason)
                        break
                except json.JSONDecodeError:
                    pass
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.warning("Error in WS receiver loop for job %s: %s", job_id, e)


connection_manager = ConnectionManager()
