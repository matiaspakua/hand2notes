"""SQLModel table definitions backing the hand2notes SQLite database.

Relational columns cover the queryable scalar fields; nested structures
(bounding boxes, visual semantics, table/diagram payloads, metrics) are stored
as JSON columns. Conversion to/from the canonical Pydantic models in
`hand2notes.core_models` lives in the repository/service layer.
"""

from datetime import datetime
from uuid import UUID, uuid4

from hand2notes.core_models.enums import (
    ArtifactType,
    BlockType,
    PipelineStage,
    ReviewStatus,
    RunStatus,
    SessionStatus,
)
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class SessionTable(SQLModel, table=True):
    __tablename__ = "session"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    notebook: str
    topic: str | None = None
    created_at: datetime
    status: SessionStatus = Field(default=SessionStatus.CREATED)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class PageTable(SQLModel, table=True):
    __tablename__ = "page"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="session.id", index=True)
    sequence: int
    source_path: str
    preprocessed_path: str | None = None
    width_px: int
    height_px: int
    pipeline_stage: PipelineStage = Field(default=PipelineStage.IMPORT)
    overall_confidence: float = 0.0
    review_status: ReviewStatus = Field(default=ReviewStatus.PENDING)


class BlockTable(SQLModel, table=True):
    __tablename__ = "block"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    page_id: UUID = Field(foreign_key="page.id", index=True)
    block_type: BlockType
    reading_order: int
    bbox: dict = Field(default_factory=dict, sa_column=Column(JSON))
    confidence: float
    review_flag: bool = False
    content: str | None = None
    corrected_content: str | None = None
    visual_semantics: dict | None = Field(default=None, sa_column=Column(JSON))
    crop_path: str | None = None
    # Specialization payloads — populated only for table/diagram blocks.
    table_data: dict | None = Field(default=None, sa_column=Column(JSON))
    diagram_data: dict | None = Field(default=None, sa_column=Column(JSON))


class ExportArtifactTable(SQLModel, table=True):
    __tablename__ = "export_artifact"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="session.id", index=True)
    page_id: UUID | None = Field(default=None, foreign_key="page.id", index=True)
    artifact_type: ArtifactType
    file_path: str
    vault_relative_path: str
    created_at: datetime


class PipelineRunTable(SQLModel, table=True):
    __tablename__ = "pipeline_run"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="session.id", index=True)
    stage: PipelineStage
    started_at: datetime
    completed_at: datetime | None = None
    status: RunStatus = Field(default=RunStatus.RUNNING)
    error: str | None = None
    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
