"""Session API router: create, list, get, update, and delete sessions."""

import logging
import mimetypes
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from hand2notes.core_models.enums import SessionStatus
from hand2notes.core_models.models import Page, Session
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

_UPLOAD_DIR = Path.home() / ".config" / "hand2notes" / "uploads"

# In-memory session store (replaced by DB persistence in Phase 5)
_sessions: dict[UUID, Session] = {}
_session_pages: dict[UUID, list[Page]] = {}


class CreateSessionRequest(BaseModel):
    name: str
    notebook: str
    topic: str | None = None
    tags: list[str] = []


class PatchSessionRequest(BaseModel):
    name: str | None = None
    notebook: str | None = None
    topic: str | None = None
    tags: list[str] | None = None
    status: SessionStatus | None = None


class ReorderPagesRequest(BaseModel):
    page_ids: list[UUID]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Session)
async def create_session(body: CreateSessionRequest) -> Session:
    session = Session(
        name=body.name,
        notebook=body.notebook,
        topic=body.topic,
        tags=body.tags,
    )
    _sessions[session.id] = session
    _session_pages[session.id] = []
    log.info(
        "Session created: id=%s name=%r notebook=%r tags=%s",
        session.id, session.name, session.notebook, session.tags,
    )
    return session


@router.get("", response_model=list[Session])
async def list_sessions() -> list[Session]:
    return list(_sessions.values())


@router.get("/{session_id}", response_model=Session)
async def get_session_by_id(session_id: UUID) -> Session:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.pages = _session_pages.get(session_id, [])
    return session


@router.patch("/{session_id}", response_model=Session)
async def patch_session(session_id: UUID, body: PatchSessionRequest) -> Session:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.name is not None:
        session.name = body.name
    if body.notebook is not None:
        session.notebook = body.notebook
    if body.topic is not None:
        session.topic = body.topic
    if body.tags is not None:
        session.tags = body.tags
    if body.status is not None:
        session.status = body.status
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID) -> None:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions.pop(session_id)
    page_count = len(_session_pages.pop(session_id, []))
    log.info("Session deleted: id=%s name=%r pages=%d", session_id, session.name, page_count)


@router.post(
    "/{session_id}/pages", status_code=status.HTTP_201_CREATED, response_model=list[Page]
)
async def upload_pages(session_id: UUID, files: list[UploadFile]) -> list[Page]:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from hand2notes.ingestion.importer import ImportError as IngestError
    from hand2notes.ingestion.importer import import_image

    upload_dir = _UPLOAD_DIR / str(session_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    existing = _session_pages.get(session_id, [])
    next_sequence = len(existing) + 1
    new_pages: list[Page] = []
    filenames = [f.filename or f"page_{next_sequence + i}" for i, f in enumerate(files)]

    log.info(
        "Page upload started: session=%s file_count=%d files=%s",
        session_id, len(files), filenames,
    )

    for file in files:
        dest = upload_dir / (file.filename or f"page_{next_sequence}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            page = import_image(dest, session_id, sequence=next_sequence)
        except IngestError as exc:
            log.error(
                "Page ingest failed: session=%s file=%s error=%s",
                session_id, file.filename, exc,
            )
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        log.debug(
            "Page ingested: session=%s page_id=%s sequence=%d size=%dx%d path=%s",
            session_id, page.id, page.sequence, page.width_px, page.height_px, dest.name,
        )
        new_pages.append(page)
        next_sequence += 1

    existing.extend(new_pages)
    _session_pages[session_id] = existing
    log.info(
        "Page upload complete: session=%s added=%d total_pages=%d",
        session_id, len(new_pages), len(existing),
    )
    return new_pages


@router.patch("/{session_id}/pages/reorder", response_model=list[Page])
async def reorder_pages(session_id: UUID, body: ReorderPagesRequest) -> list[Page]:
    pages = _session_pages.get(session_id, [])
    page_map = {p.id: p for p in pages}
    reordered = []
    for i, pid in enumerate(body.page_ids, start=1):
        page = page_map.get(pid)
        if not page:
            raise HTTPException(status_code=422, detail=f"Page {pid} not in session")
        page.sequence = i
        reordered.append(page)
    _session_pages[session_id] = reordered
    return reordered


@router.get("/{session_id}/pages/{page_id}/image")
async def get_page_image(session_id: UUID, page_id: UUID) -> FileResponse:
    """Serve the (preprocessed) page image for canvas display in the UI."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    pages = _session_pages.get(session_id, [])
    page = next((p for p in pages if p.id == page_id), None)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Prefer the preprocessed image (correct scale for block bboxes); fall back to source
    image_path: Path = page.preprocessed_path or page.source_path
    if not image_path.exists():
        log.warning(
            "Image file missing: session=%s page=%s path=%s", session_id, page_id, image_path
        )
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    media_type, _ = mimetypes.guess_type(str(image_path))
    return FileResponse(str(image_path), media_type=media_type or "image/jpeg")
