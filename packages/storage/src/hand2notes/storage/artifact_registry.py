"""Registry for tracking generated output files (ExportArtifact records)."""

from uuid import UUID

from hand2notes.core_models.models import ExportArtifact
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .db_models import ExportArtifactTable


def _to_table(artifact: ExportArtifact) -> ExportArtifactTable:
    return ExportArtifactTable(
        id=artifact.id,
        session_id=artifact.session_id,
        page_id=artifact.page_id,
        artifact_type=artifact.artifact_type,
        file_path=str(artifact.file_path),
        vault_relative_path=artifact.vault_relative_path,
        created_at=artifact.created_at,
    )


def _to_model(row: ExportArtifactTable) -> ExportArtifact:
    return ExportArtifact.model_validate(
        {
            "id": row.id,
            "session_id": row.session_id,
            "page_id": row.page_id,
            "artifact_type": row.artifact_type,
            "file_path": row.file_path,
            "vault_relative_path": row.vault_relative_path,
            "created_at": row.created_at,
        }
    )


async def register(session: AsyncSession, artifact: ExportArtifact) -> ExportArtifact:
    """Persist one artifact record and return the stored model."""
    row = _to_table(artifact)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_model(row)


async def list_for_session(session: AsyncSession, session_id: UUID) -> list[ExportArtifact]:
    """Return all artifacts recorded for a session, oldest first."""
    result = await session.exec(
        select(ExportArtifactTable)
        .where(ExportArtifactTable.session_id == session_id)
        .order_by(ExportArtifactTable.created_at)
    )
    return [_to_model(row) for row in result.all()]
