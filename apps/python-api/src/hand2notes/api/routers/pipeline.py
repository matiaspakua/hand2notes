"""Pipeline API router: process, cancel, run status, WebSocket progress, and diagram review."""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from hand2notes.core_models.blocks import DiagramBlock
from hand2notes.core_models.enums import DiagramDecision
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

    log.info(
        "Pipeline run starting: session=%s run_id=%s page_count=%d vault_root=%s",
        session_id, run_id, len(pages), config.vault_root,
    )

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
            log.info("Pipeline run completed: session=%s run_id=%s", session_id, run_id)
        except PipelineError as exc:
            log.error("Pipeline stage failed: session=%s run_id=%s error=%s", session_id, run_id, exc)
            on_progress({"event": "run_failed", "error": str(exc)})
        except asyncio.CancelledError:
            log.info("Pipeline run cancelled: session=%s run_id=%s", session_id, run_id)
            on_progress({"event": "run_cancelled"})
        except Exception as exc:
            log.exception(
                "Pipeline run crashed unexpectedly: session=%s run_id=%s error=%s: %s",
                session_id, run_id, type(exc).__name__, exc,
            )
            on_progress({"event": "run_failed", "error": f"{type(exc).__name__}: {exc}"})
        finally:
            _active_runs.pop(session_id, None)
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
    log.info("Pipeline cancellation requested: session=%s run_id=%s", session_id, run_id)
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
    log.info("Progress WebSocket connected: session=%s", session_id)

    queue: asyncio.Queue = asyncio.Queue()
    _progress_queues.setdefault(session_id, []).append(queue)

    try:
        while True:
            event = await queue.get()
            if event.get("event") == "__done__":
                break
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        log.info("Progress WebSocket disconnected by client: session=%s", session_id)
    finally:
        queues = _progress_queues.get(session_id, [])
        if queue in queues:
            queues.remove(queue)
        log.debug("Progress WebSocket cleaned up: session=%s remaining=%d", session_id, len(queues))


# ---------------------------------------------------------------------------
# Diagram review endpoints (US2)
# ---------------------------------------------------------------------------

class DiagramReviewPatch(BaseModel):
    review_decision: str  # approved | rejected | deferred


def _find_page(session_id: UUID, page_id: UUID):
    pages = _session_pages.get(session_id, [])
    for p in pages:
        if p.id == page_id:
            return p
    return None


def _find_diagram_block(page, block_id: UUID) -> DiagramBlock | None:
    for b in page.blocks:
        if isinstance(b, DiagramBlock) and b.id == block_id:
            return b
    return None


@router.patch("/{session_id}/pages/{page_id}/diagrams/{block_id}")
async def patch_diagram_review(
    session_id: UUID,
    page_id: UUID,
    block_id: UUID,
    body: DiagramReviewPatch,
) -> dict:
    """Set the review decision (approved/rejected/deferred) for a diagram block."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    page = _find_page(session_id, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    block = _find_diagram_block(page, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Diagram block not found")

    try:
        decision = DiagramDecision(body.review_decision)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid review_decision; must be one of: {[d.value for d in DiagramDecision]}",
        )

    block.review_decision = decision
    return {
        "block_id": str(block.id),
        "review_decision": block.review_decision.value,
        "diagram_type": block.diagram_type.value,
        "reconstruction_confidence": block.reconstruction_confidence,
    }


# ---------------------------------------------------------------------------
# Export endpoints (US5)
# ---------------------------------------------------------------------------

# Track per-session export artifacts in memory
_export_artifacts: dict[UUID, list] = {}


@router.post("/{session_id}/export", status_code=status.HTTP_202_ACCEPTED)
async def export_session(session_id: UUID) -> dict:
    """Trigger vault export for a session using the configured export mode."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    pages = _session_pages.get(session_id, [])
    config = _default_config()

    if not config.vault_root:
        raise HTTPException(
            status_code=422,
            detail="vault_root is not configured. Set it via PUT /config first.",
        )

    from hand2notes.markdown_export.renderer import render_note
    from hand2notes.markdown_export.vault_writer import write_note

    markdown = render_note(session, pages, config)
    artifacts = write_note(config, session, markdown, pages=pages)
    _export_artifacts[session_id] = artifacts

    from hand2notes.core_models.enums import SessionStatus
    session.status = SessionStatus.EXPORTED

    return {
        "session_id": str(session_id),
        "message": "Export started",
        "artifacts_count": len(artifacts),
    }


@router.get("/{session_id}/export/status")
async def export_status(session_id: UUID) -> dict:
    """Return the artifact list and export status for a session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    artifacts = _export_artifacts.get(session_id, [])
    return {
        "session_id": str(session_id),
        "session_status": session.status.value,
        "artifacts": [
            {
                "artifact_type": a.artifact_type.value,
                "vault_relative_path": a.vault_relative_path,
                "file_path": str(a.file_path),
            }
            for a in artifacts
        ],
    }


# ---------------------------------------------------------------------------
# Review and correction endpoints (US6)
# ---------------------------------------------------------------------------

class BlockCorrectionPatch(BaseModel):
    corrected_content: str | None = None
    review_flag: bool = False


@router.get("/{session_id}/pages/{page_id}/review")
async def get_page_review_full(session_id: UUID, page_id: UUID) -> dict:
    """Return full review payload for a page, including Markdown preview."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    page = _find_page(session_id, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    from hand2notes.review.review_builder import build_review_payload
    config = _default_config()
    return build_review_payload(session, page, config)


@router.patch("/{session_id}/pages/{page_id}/blocks/{block_id}")
async def patch_block(
    session_id: UUID,
    page_id: UUID,
    block_id: UUID,
    body: BlockCorrectionPatch,
) -> dict:
    """Apply a text correction to a block."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    page = _find_page(session_id, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    from hand2notes.review.correction_service import apply_correction
    block = apply_correction(
        page,
        block_id,
        corrected_content=body.corrected_content or "",
        review_flag=body.review_flag,
    )
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")

    return {
        "block_id": str(block.id),
        "block_type": block.block_type.value,
        "content": block.content,
        "auto_corrected_content": block.auto_corrected_content,
        "corrected_content": block.corrected_content,
        "effective_content": block.effective_content,
        "review_flag": block.review_flag,
        "confidence": block.confidence,
    }
