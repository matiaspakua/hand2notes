"""Canonical string enums shared across the hand2notes pipeline."""

from enum import StrEnum


class PipelineStage(StrEnum):
    IMPORT = "import"
    PREPROCESS = "preprocess"
    DETECT_LAYOUT = "detect_layout"
    RECOGNIZE_TEXT = "recognize_text"
    TEXT_CORRECTION = "text_correction"
    RECONSTRUCT_STRUCTURE = "reconstruct_structure"
    DETECT_DIAGRAMS = "detect_diagrams"
    GENERATE_OUTPUT = "generate_output"
    REVIEW = "review"
    EXPORT = "export"


class SessionStatus(StrEnum):
    CREATED = "created"
    PROCESSING = "processing"
    REVIEW = "review"
    EXPORTED = "exported"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FLAGGED = "flagged"


class ExportMode(StrEnum):
    OVERWRITE = "overwrite"
    VERSIONED = "versioned"
    MERGE = "merge"


class VLMRuntime(StrEnum):
    LLAMACPP = "llamacpp"
    OLLAMA = "ollama"


class FallbackType(StrEnum):
    CSV = "csv"
    HTML = "html"
    IMAGE = "image"


class DiagramDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(StrEnum):
    MARKDOWN = "markdown"
    PLANTUML = "plantuml"
    DRAWIO = "drawio"
    MERMAID = "mermaid"
    CSV = "csv"
    IMAGE_ASSET = "image_asset"
    METADATA_JSON = "metadata_json"


class EdgeDirection(StrEnum):
    FORWARD = "forward"
    BACKWARD = "backward"
    BIDIRECTIONAL = "bidirectional"
    UNDIRECTED = "undirected"


class BlockType(StrEnum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    TABLE = "table"
    DIAGRAM = "diagram"
    CALLOUT = "callout"
    MARGINAL_NOTE = "marginal_note"
    ARROW_CONNECTOR = "arrow_connector"
    EMBEDDED_IMAGE = "embedded_image"
    URL_REFERENCE = "url_reference"
    FORMULA = "formula"


class DiagramType(StrEnum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    UML_CLASS = "uml_class"
    UML_ACTIVITY = "uml_activity"
    BLOCK_DIAGRAM = "block_diagram"
    ARCHITECTURE = "architecture"
    GRAPH_NETWORK = "graph_network"
    ANNOTATED_SKETCH = "annotated_sketch"
    CHART_PLOT = "chart_plot"
    UNKNOWN = "unknown"


class DiagramFormat(StrEnum):
    PLANTUML = "plantuml"
    DRAWIO = "drawio"
    MERMAID = "mermaid"
