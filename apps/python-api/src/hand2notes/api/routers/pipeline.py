"""Pipeline API router: process, cancel, run status, and WebSocket progress stream."""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from hand2notes.core_models.models import VaultConfig
from pydantic import BaseModel

from hand2notes.pipeline.orchestrator import PipelineError, run_pipeline

from .sessions import _session_pages, _sessions

log = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["pipeline"])

# Active pipeline runs: session_id → (asyncio.Task, asyncio.Event for cancel)
_active_runs: dict[UUID, tuple[asyncio.Task, asyncio.Event]] = {}
# Progress queues: session_id → list of WebSocket connections
_progress_queues: dict[UUID, list[asyncio.Queue]] = {}


def _default_config() -> VaultConfig:
    """Load config from ~/.config/hand2notes/config.json or return defaults."""
    from pathlib import Path
    config_path = Path.home() / ".config" / "hand2notes" / "config.json"
    if config_path.exists():
        import json as _json
        try:
            data = _json.loads(config_path.read_text())
            return VaultConfig.model_validate(data)
        except Exception:
            pass
    return VaultConfig()


class ProcessResponse(BaseModel):
    run_id: str
    session_id: str
    message: str


@router.post(
    "/{session_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProcessResponse,
)
async def start_processing(session_id: UUID) -> ProcessResponse:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_id in _active_runs:
        raise HTTPException(
            status_code=409,
            detail="A pipeline run is already active for this session",
        )

    pages = _session_pages.get(session_id, [])
    if not pages:
        raise HTTPException(status_code=422, detail="Session has no pages to process")

    config = _default_config()
    cancel_event = asyncio.Event()
    run_id = str(session.id) + "-run"

    def on_progress(event: dict[str, Any]) -> None:
        queues = _progress_queues.get(session_id, [])
        for q in queues:
            q.put_nowait(event)

    async def _run() -> None:
        try:
            await run_pipeline(
                db=None,  # type: ignore[arg-type]  # DB wired in Phase 5
                session=session,
                pages=pages,
                config=config,
                on_progress=on_progress,
                cancelled=cancel_event,
            )
        except PipelineError as exc:
            on_progress({"event": "run_failed", "error": str(exc)})
        except asyncio.CancelledError:
            on_progress({"event": "run_cancelled"})
        except Exception as exc:  # never let the UI hang on an unexpected error
            log.exception("Pipeline run crashed")
            on_progress({"event": "run_failed", "error": f"{type(exc).__name__}: {exc}"})
        finally:
            _active_runs.pop(session_id, None)
            # Signal all progress WebSockets to close
            for q in _progress_queues.get(session_id, []):
                q.put_nowait({"event": "__done__"})

    task = asyncio.create_task(_run())
    _active_runs[session_id] = (task, cancel_event)

    return ProcessResponse(run_id=run_id, session_id=str(session_id), message="Pipeline started")


@router.post("/{session_id}/runs/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_run(session_id: UUID, run_id: str) -> dict:
    entry = _active_runs.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No active run for this session")
    task, cancel_event = entry
    cancel_event.set()
    return {"message": "Cancellation requested"}


@router.get("/{session_id}/runs/{run_id}", response_model=dict)
async def get_run_status(session_id: UUID, run_id: str) -> dict:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    is_active = session_id in _active_runs
    return {
        "run_id": run_id,
        "session_id": str(session_id),
        "session_status": session.status.value,
        "is_active": is_active,
    }


@router.websocket("/{session_id}/progress")
async def progress_websocket(websocket: WebSocket, session_id: UUID) -> None:
    """Stream pipeline progress events as JSON frames over WebSocket."""
    await websocket.accept()

    queue: asyncio.Queue = asyncio.Queue()
    _progress_queues.setdefault(session_id, []).append(queue)

    try:
        while True:
            event = await queue.get()
            if event.get("event") == "__done__":
                break
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        queues = _progress_queues.get(session_id, [])
        if queue in queues:
            queues.remove(queue)
