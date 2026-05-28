"""Session API router: create, list, get, update, and delete sessions."""

import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from hand2notes.core_models.enums import SessionStatus
from hand2notes.core_models.models import Page, Session
from pydantic import BaseModel

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
    _sessions.pop(session_id)
    _session_pages.pop(session_id, None)


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

    for file in files:
        dest = upload_dir / (file.filename or f"page_{next_sequence}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            page = import_image(dest, session_id, sequence=next_sequence)
        except IngestError as exc:
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        new_pages.append(page)
        next_sequence += 1

    existing.extend(new_pages)
    _session_pages[session_id] = existing
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
