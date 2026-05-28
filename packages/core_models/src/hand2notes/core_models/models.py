"""Core Pydantic v2 data models for the hand2notes pipeline.

Every content-bearing entity carries source coordinates and confidence metadata,
per constitution Principle III (Fidelity Over Silence).
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import (
    ArtifactType,
    BlockType,
    ExportMode,
    PipelineStage,
    ReviewStatus,
    RunStatus,
    SessionStatus,
    VLMRuntime,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BoundingBox(BaseModel):
    """Source pixel coordinates for a detected region."""

    x: int = Field(ge=0, description="Left edge in pixels")
    y: int = Field(ge=0, description="Top edge in pixels")
    width: int = Field(gt=0, description="Width in pixels")
    height: int = Field(gt=0, description="Height in pixels")


class VisualSemantics(BaseModel):
    """Visual emphasis metadata that cannot always render directly in Markdown."""

    highlight_color: str | None = Field(
        default=None, description="CSS color name or hex, e.g. 'yellow' or '#FFFF00'"
    )
    is_underlined: bool = False
    is_boxed: bool = False
    is_circled: bool = False
    callout_label: str | None = Field(
        default=None, description="Callout label or arrow annotation text"
    )
    obsidian_notation: str | None = Field(
        default=None, description="Pre-rendered Obsidian notation, e.g. '==text=='"
    )


class Block(BaseModel):
    """A detected region on a page with typed content."""

    id: UUID = Field(default_factory=uuid4)
    page_id: UUID
    block_type: BlockType
    reading_order: int = Field(ge=0, description="0-based reading order index on the page")
    bbox: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0, description="OCR/detection confidence")
    review_flag: bool = Field(
        default=False, description="True if below threshold or manually flagged"
    )
    content: str | None = Field(default=None, description="Extracted text content")
    auto_corrected_content: str | None = Field(
        default=None, description="Automatic spell-correction result; set by text_correction stage"
    )
    corrected_content: str | None = Field(
        default=None, description="User-corrected text; overrides all automatic corrections"
    )
    visual_semantics: VisualSemantics | None = None
    crop_path: Path | None = Field(default=None, description="Saved crop image for this block")

    @property
    def effective_content(self) -> str | None:
        """Text used on export: user correction > auto spell-correction > raw OCR."""
        if self.corrected_content is not None:
            return self.corrected_content
        if self.auto_corrected_content is not None:
            return self.auto_corrected_content
        return self.content


class Page(BaseModel):
    """One notebook page and all data derived from it."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    sequence: int = Field(ge=1, description="1-based page order within the session")
    source_path: Path
    preprocessed_path: Path | None = None
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    blocks: list[Block] = Field(default_factory=list)
    pipeline_stage: PipelineStage = PipelineStage.IMPORT
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.PENDING


class ExportArtifact(BaseModel):
    """One generated output file (note, diagram source, CSV, image asset, metadata)."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    page_id: UUID | None = Field(default=None, description="None for session-level artifacts")
    artifact_type: ArtifactType
    file_path: Path
    vault_relative_path: str = Field(description="Path relative to vault root for Obsidian links")
    created_at: datetime = Field(default_factory=_utcnow)


class Session(BaseModel):
    """Top-level container for one note-taking event."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    notebook: str
    topic: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    status: SessionStatus = SessionStatus.CREATED
    pages: list[Page] = Field(default_factory=list)
    export_artifact: ExportArtifact | None = None
    tags: list[str] = Field(default_factory=list)


class PipelineRun(BaseModel):
    """Audit log entry for one execution of the full pipeline or a single stage."""

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    stage: PipelineStage
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = None
    status: RunStatus = RunStatus.RUNNING
    error: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)


class VaultConfig(BaseModel):
    """User-configured Obsidian vault settings. One instance per installation."""

    vault_root: Path | None = Field(default=None, description="Absolute path to the vault root")
    folder_template: str = Field(
        default="{{notebook}}/{{date}}-{{topic}}",
        description="Jinja2 template for the session subfolder",
    )
    export_mode: ExportMode = ExportMode.OVERWRITE
    default_notebook: str | None = None
    front_matter_fields: dict[str, str] = Field(default_factory=dict)
    vlm_runtime: VLMRuntime = VLMRuntime.OLLAMA
    vlm_model: str = "qwen2.5vl:7b"
    ocr_languages: list[str] = Field(default_factory=lambda: ["es", "en"])
    confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    spell_correction_enabled: bool = Field(
        default=True,
        description="Run post-OCR spell correction (Spanish + English)",
    )
    spell_correction_languages: list[str] = Field(
        default_factory=lambda: ["es", "en"],
        description="Language codes passed to the spell corrector",
    )
