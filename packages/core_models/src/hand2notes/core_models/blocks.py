"""Specialized block models for tables and diagrams.

Both extend `Block` and carry structure-specific reconstruction data plus a
fallback path, so no table or diagram is ever silently lost (constitution III).
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .enums import (
    BlockType,
    DiagramDecision,
    DiagramFormat,
    DiagramType,
    EdgeDirection,
    FallbackType,
)
from .models import Block, BoundingBox


class DiagramNode(BaseModel):
    """A node extracted from a diagram by the VLM."""

    id: str = Field(description="Node identifier from VLM output")
    label: str = Field(description="Node display label")
    node_type: str | None = Field(
        default=None, description="e.g. 'process', 'decision', 'database', 'actor'"
    )
    bbox: BoundingBox | None = Field(default=None, description="Source coordinates if localized")


class DiagramEdge(BaseModel):
    """A connector between two diagram nodes."""

    source_id: str
    target_id: str
    label: str | None = None
    direction: EdgeDirection = EdgeDirection.FORWARD


class TableBlock(Block):
    """A `Block` reconstructed into structured rows and columns."""

    block_type: BlockType = BlockType.TABLE
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list, description="Cell values, row-major")
    caption: str | None = None
    reconstruction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    fallback_type: FallbackType | None = Field(
        default=None, description="Set when Markdown reconstruction is not recoverable"
    )
    fallback_path: Path | None = None


class DiagramBlock(Block):
    """A `Block` classified as a diagram, with reconstruction and review data."""

    block_type: BlockType = BlockType.DIAGRAM
    diagram_type: DiagramType = DiagramType.UNKNOWN
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    vlm_json_raw: dict[str, Any] | None = Field(
        default=None, description="Raw constrained JSON from the VLM before validation"
    )
    generated_source_path: Path | None = Field(
        default=None, description="PlantUML / draw.io / Mermaid output file"
    )
    generated_format: DiagramFormat | None = None
    generated_png_path: Path | None = Field(
        default=None, description="PNG export of the generated source — embedded in Markdown"
    )
    crop_path: Path = Field(description="Original crop — always preserved")
    reconstruction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    review_decision: DiagramDecision = DiagramDecision.PENDING
