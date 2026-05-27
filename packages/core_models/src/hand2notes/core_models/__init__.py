"""Canonical Pydantic v2 data models for the hand2notes pipeline."""

from .blocks import DiagramBlock, DiagramEdge, DiagramNode, TableBlock
from .enums import (
    ArtifactType,
    BlockType,
    DiagramDecision,
    DiagramFormat,
    DiagramType,
    EdgeDirection,
    ExportMode,
    FallbackType,
    PipelineStage,
    ReviewStatus,
    RunStatus,
    SessionStatus,
    VLMRuntime,
)
from .models import (
    Block,
    BoundingBox,
    ExportArtifact,
    Page,
    PipelineRun,
    Session,
    VaultConfig,
    VisualSemantics,
)

__all__ = [
    # models
    "BoundingBox",
    "VisualSemantics",
    "Block",
    "Page",
    "ExportArtifact",
    "Session",
    "PipelineRun",
    "VaultConfig",
    # blocks
    "TableBlock",
    "DiagramBlock",
    "DiagramNode",
    "DiagramEdge",
    # enums
    "PipelineStage",
    "SessionStatus",
    "ReviewStatus",
    "ExportMode",
    "VLMRuntime",
    "FallbackType",
    "DiagramDecision",
    "RunStatus",
    "ArtifactType",
    "EdgeDirection",
    "BlockType",
    "DiagramType",
    "DiagramFormat",
]
