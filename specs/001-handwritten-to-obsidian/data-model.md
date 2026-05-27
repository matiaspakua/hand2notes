# Data Model: Handwritten Notes to Obsidian Vault

**Phase**: 1 — Design
**Date**: 2026-05-27
**Plan**: [plan.md](./plan.md)

All entities are defined as Pydantic v2 models in `packages/core_models/`.
Every entity carries source coordinates and confidence metadata per the constitution.

---

## VaultConfig

Persisted as JSON in the app config directory. One instance per installation.

| Field | Type | Description |
|-------|------|-------------|
| `vault_root` | `Path` | Absolute path to the Obsidian vault root folder |
| `folder_template` | `str` | Jinja2 template for session subfolder, e.g. `{{notebook}}/{{date}}-{{topic}}` |
| `export_mode` | `ExportMode` | `overwrite` \| `versioned` \| `merge` |
| `default_notebook` | `str \| None` | Default notebook name used when not specified per session |
| `front_matter_fields` | `dict[str, str]` | Custom YAML front matter field mappings |
| `vlm_runtime` | `VLMRuntime` | `llamacpp` \| `ollama` |
| `vlm_model` | `str` | Model identifier, e.g. `qwen2.5vl:7b` or GGUF path |

---

## Session

Top-level container for one note-taking event.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Unique session identifier |
| `name` | `str` | User-supplied session name |
| `notebook` | `str` | Notebook or course name |
| `topic` | `str \| None` | Session topic / subject |
| `created_at` | `datetime` | Session creation timestamp |
| `status` | `SessionStatus` | `created` \| `processing` \| `review` \| `exported` \| `failed` |
| `pages` | `list[Page]` | Ordered list of pages in this session |
| `export_artifact` | `ExportArtifact \| None` | Reference to the exported Markdown note |
| `tags` | `list[str]` | Obsidian tags to include in front matter |

**State transitions**: `created` → `processing` → `review` → `exported`
Failures at any stage transition to `failed` with an error log entry.

---

## Page

One notebook page and all data derived from it.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Unique page identifier |
| `session_id` | `UUID` | Parent session |
| `sequence` | `int` | 1-based page order within session |
| `source_path` | `Path` | Absolute path to original image file |
| `preprocessed_path` | `Path \| None` | Path to preprocessed image output |
| `width_px` | `int` | Image width in pixels |
| `height_px` | `int` | Image height in pixels |
| `blocks` | `list[Block]` | Detected content blocks in reading order |
| `pipeline_stage` | `PipelineStage` | Last completed pipeline stage for this page |
| `overall_confidence` | `float` | Aggregate confidence score 0.0–1.0 |
| `review_status` | `ReviewStatus` | `pending` \| `in_review` \| `approved` \| `flagged` |

---

## Block

A detected region on a page with typed content.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Unique block identifier |
| `page_id` | `UUID` | Parent page |
| `block_type` | `BlockType` | See BlockType enum below |
| `reading_order` | `int` | 0-based reading order index on the page |
| `bbox` | `BoundingBox` | Source coordinates: x, y, width, height (pixels) |
| `confidence` | `float` | OCR/detection confidence 0.0–1.0 |
| `review_flag` | `bool` | True if confidence below threshold or manually flagged |
| `content` | `str \| None` | Extracted text content (for text-type blocks) |
| `corrected_content` | `str \| None` | User-corrected text (overrides content on export) |
| `visual_semantics` | `VisualSemantics \| None` | Highlight, color, underline, box metadata |
| `crop_path` | `Path \| None` | Saved crop image for this block |

**BlockType enum**: `title` \| `heading` \| `paragraph` \| `bullet_list` \|
`numbered_list` \| `table` \| `diagram` \| `callout` \| `marginal_note` \|
`arrow_connector` \| `embedded_image` \| `url_reference` \| `formula`

---

## BoundingBox

Reusable value object for spatial coordinates.

| Field | Type | Description |
|-------|------|-------------|
| `x` | `int` | Left edge in pixels |
| `y` | `int` | Top edge in pixels |
| `width` | `int` | Width in pixels |
| `height` | `int` | Height in pixels |

---

## VisualSemantics

Metadata capturing visual emphasis that cannot be rendered directly in Markdown.

| Field | Type | Description |
|-------|------|-------------|
| `highlight_color` | `str \| None` | CSS-style color name or hex, e.g. `yellow`, `#FFFF00` |
| `is_underlined` | `bool` | Text contains underline marker |
| `is_boxed` | `bool` | Region is enclosed in a drawn box |
| `is_circled` | `bool` | Region is enclosed in a drawn circle |
| `callout_label` | `str \| None` | Text of the callout label or arrow annotation |
| `obsidian_notation` | `str \| None` | Pre-rendered Obsidian notation, e.g. `==text==` |

---

## TableBlock

Extends Block; carries structured table data.

| Field | Type | Description |
|-------|------|-------------|
| `headers` | `list[str]` | Column header values |
| `rows` | `list[list[str]]` | Table cell values, row-major |
| `caption` | `str \| None` | Table caption or nearby label |
| `reconstruction_confidence` | `float` | Table-specific confidence score |
| `fallback_type` | `FallbackType \| None` | `csv` \| `html` \| `image` if Markdown not recoverable |
| `fallback_path` | `Path \| None` | Path to fallback file |

---

## DiagramBlock

Extends Block; carries diagram reconstruction data.

| Field | Type | Description |
|-------|------|-------------|
| `diagram_type` | `DiagramType` | See DiagramType enum below |
| `nodes` | `list[DiagramNode]` | Extracted nodes |
| `edges` | `list[DiagramEdge]` | Extracted edges/connectors |
| `vlm_json_raw` | `dict \| None` | Raw constrained JSON from VLM before validation |
| `generated_source_path` | `Path \| None` | PlantUML / draw.io / Mermaid file path |
| `generated_format` | `DiagramFormat \| None` | `plantuml` \| `drawio` \| `mermaid` |
| `crop_path` | `Path` | Original crop — always preserved |
| `reconstruction_confidence` | `float` | Diagram-specific confidence |
| `review_decision` | `DiagramDecision` | `pending` \| `approved` \| `rejected` \| `deferred` |

**DiagramType enum**: `flowchart` \| `sequence` \| `uml_class` \| `uml_activity` \|
`block_diagram` \| `architecture` \| `graph_network` \| `annotated_sketch` \| `chart_plot` \| `unknown`

**DiagramFormat enum**: `plantuml` \| `drawio` \| `mermaid`

---

## DiagramNode

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Node identifier (from VLM output) |
| `label` | `str` | Node display label |
| `node_type` | `str \| None` | e.g. `process`, `decision`, `database`, `actor` |
| `bbox` | `BoundingBox \| None` | Source coordinates if localized |

---

## DiagramEdge

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Source node ID |
| `target_id` | `str` | Target node ID |
| `label` | `str \| None` | Edge label |
| `direction` | `EdgeDirection` | `forward` \| `backward` \| `bidirectional` \| `undirected` |

---

## ExportArtifact

One generated output file.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Unique artifact identifier |
| `session_id` | `UUID` | Parent session |
| `page_id` | `UUID \| None` | Parent page (None for session-level artifacts) |
| `artifact_type` | `ArtifactType` | `markdown` \| `plantuml` \| `drawio` \| `mermaid` \| `csv` \| `image_asset` \| `metadata_json` |
| `file_path` | `Path` | Absolute path to the file on disk |
| `vault_relative_path` | `str` | Path relative to vault root for Obsidian links |
| `created_at` | `datetime` | Generation timestamp |

---

## PipelineRun

Audit log for one execution of the full pipeline or a single stage.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Unique run identifier |
| `session_id` | `UUID` | Session being processed |
| `stage` | `PipelineStage` | Which stage ran |
| `started_at` | `datetime` | Stage start time |
| `completed_at` | `datetime \| None` | Stage completion time |
| `status` | `RunStatus` | `running` \| `completed` \| `failed` \| `cancelled` |
| `error` | `str \| None` | Structured error message if failed |
| `metrics` | `dict[str, float]` | Stage-specific metrics (e.g. `blocks_detected`, `confidence_mean`) |

---

## Key Enums

```
PipelineStage:    import | preprocess | detect_layout | recognize_text |
                  reconstruct_structure | detect_diagrams | generate_output |
                  review | export

SessionStatus:    created | processing | review | exported | failed

ReviewStatus:     pending | in_review | approved | flagged

ExportMode:       overwrite | versioned | merge

VLMRuntime:       llamacpp | ollama

FallbackType:     csv | html | image

DiagramDecision:  pending | approved | rejected | deferred

RunStatus:        running | completed | failed | cancelled

ArtifactType:     markdown | plantuml | drawio | mermaid | csv |
                  image_asset | metadata_json

EdgeDirection:    forward | backward | bidirectional | undirected
```

---

## Entity Relationships

```
VaultConfig (1) ─────────────────── (app-global)

Session (1)
  └── pages: Page[] (ordered)
        └── blocks: Block[] (reading order)
              ├── TableBlock (specialization)
              │     └── fallback: ExportArtifact?
              └── DiagramBlock (specialization)
                    ├── nodes: DiagramNode[]
                    ├── edges: DiagramEdge[]
                    └── generated_source: ExportArtifact?

Session (1)
  └── export_artifact: ExportArtifact? (session-level notes.md)

PipelineRun (many) ──────────────── Session (1)
```
