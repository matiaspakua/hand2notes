"""PipelineRun lifecycle management — create, complete, fail, and query run records."""

from datetime import UTC, datetime
from uuid import UUID

from hand2notes.core_models.enums import PipelineStage, RunStatus
from hand2notes.core_models.models import PipelineRun
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .db_models import PipelineRunTable


def _to_table(run: PipelineRun) -> PipelineRunTable:
    return PipelineRunTable(
        id=run.id,
        session_id=run.session_id,
        stage=run.stage,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status,
        error=run.error,
        metrics=run.metrics,
    )


def _to_model(row: PipelineRunTable) -> PipelineRun:
    return PipelineRun.model_validate(
        {
            "id": row.id,
            "session_id": row.session_id,
            "stage": row.stage,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
            "status": row.status,
            "error": row.error,
            "metrics": row.metrics or {},
        }
    )


async def start_run(
    session: AsyncSession,
    session_id: UUID,
    stage: PipelineStage,
) -> PipelineRun:
    """Create and persist a new PipelineRun in RUNNING state."""
    run = PipelineRun(session_id=session_id, stage=stage)
    row = _to_table(run)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_model(row)


async def complete_run(
    session: AsyncSession,
    run_id: UUID,
    metrics: dict[str, float] | None = None,
) -> PipelineRun:
    """Mark a run as COMPLETED with optional metrics."""
    row = await session.get(PipelineRunTable, run_id)
    if row is None:
        raise ValueError(f"PipelineRun {run_id} not found")
    row.status = RunStatus.COMPLETED
    row.completed_at = datetime.now(UTC)
    if metrics:
        row.metrics = metrics
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_model(row)


async def fail_run(
    session: AsyncSession,
    run_id: UUID,
    error: str,
) -> PipelineRun:
    """Mark a run as FAILED with an error message."""
    row = await session.get(PipelineRunTable, run_id)
    if row is None:
        raise ValueError(f"PipelineRun {run_id} not found")
    row.status = RunStatus.FAILED
    row.completed_at = datetime.now(UTC)
    row.error = error
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_model(row)


async def cancel_run(session: AsyncSession, run_id: UUID) -> PipelineRun:
    """Mark a run as CANCELLED."""
    row = await session.get(PipelineRunTable, run_id)
    if row is None:
        raise ValueError(f"PipelineRun {run_id} not found")
    row.status = RunStatus.CANCELLED
    row.completed_at = datetime.now(UTC)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_model(row)


async def get_runs_for_session(
    session: AsyncSession, session_id: UUID
) -> list[PipelineRun]:
    """Return all runs for a session, oldest first."""
    result = await session.exec(
        select(PipelineRunTable)
        .where(PipelineRunTable.session_id == session_id)
        .order_by(PipelineRunTable.started_at)
    )
    return [_to_model(row) for row in result.all()]
