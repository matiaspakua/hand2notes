# Tasks: Handwritten Notes to Obsidian Vault

**Input**: Design documents from `specs/001-handwritten-to-obsidian/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Tests**: Not requested in the feature specification — test tasks are omitted. Golden fixtures are included as they are required by the project constitution (Principle V).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on in-progress tasks)
- **[Story]**: Which user story this task belongs to (US1–US6)
- Exact file paths are included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Monorepo skeleton, tooling, golden fixture structure, and development environment.

- [ ] T001 Initialize monorepo directory structure: `apps/electron-ui/`, `apps/python-api/`, `packages/`, `samples/`, `tests/golden/`, `docs/` at repository root
- [ ] T002 [P] Configure Python backend project in `apps/python-api/pyproject.toml` — uv workspace, FastAPI, Uvicorn, Pydantic v2, SQLModel, OpenCV, NumPy, scikit-image, Pillow, Docling, PaddleOCR, Surya, TrOCR, python-frontmatter, Jinja2, llama-cpp-python, pytest, pytest-asyncio
- [ ] T003 [P] Configure Electron frontend project in `apps/electron-ui/package.json` — React 18, TypeScript 5.x, Electron, Motion, GSAP, markdown-it, Zustand, Vitest, ESLint, Prettier
- [ ] T004 [P] Configure ruff (linting + formatting) for Python in `apps/python-api/pyproject.toml` and ESLint + Prettier for TypeScript in `apps/electron-ui/.eslintrc.json` and `.prettierrc`
- [ ] T005 Create golden fixture directory structure: `tests/golden/layout/`, `tests/golden/tables/`, `tests/golden/diagrams/`, `tests/golden/ocr/` at repository root
- [ ] T006 [P] Initialize uv workspaces for all Python packages in `packages/` — `core_models`, `ingestion`, `preprocessing`, `layout`, `ocr`, `tables`, `diagrams`, `markdown_export`, `review`, `storage`
- [ ] T007 Configure Alembic for SQLite migrations in `apps/python-api/alembic.ini` and `apps/python-api/migrations/env.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Pydantic models, SQLite storage, FastAPI skeleton, and Electron main process — everything ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T008 Implement core Pydantic v2 models in `packages/core_models/src/hand2notes/core_models/models.py` — `VaultConfig`, `Session`, `Page`, `Block`, `BoundingBox`, `VisualSemantics`, `ExportArtifact`, `PipelineRun`
- [ ] T009 [P] Implement specialized block models in `packages/core_models/src/hand2notes/core_models/blocks.py` — `TableBlock` (headers, rows, caption, fallback_type, fallback_path), `DiagramBlock` (diagram_type, nodes, edges, vlm_json_raw, generated_source_path, review_decision), `DiagramNode`, `DiagramEdge`
- [ ] T010 [P] Implement all project enums in `packages/core_models/src/hand2notes/core_models/enums.py` — `PipelineStage`, `SessionStatus`, `ReviewStatus`, `ExportMode`, `VLMRuntime`, `FallbackType`, `DiagramType`, `DiagramFormat`, `DiagramDecision`, `ArtifactType`, `EdgeDirection`, `RunStatus`, `BlockType`
- [ ] T011 Implement SQLModel database table definitions in `packages/storage/src/hand2notes/storage/db_models.py` — SQLite-backed tables for Session, Page, Block, TableBlock, DiagramBlock, ExportArtifact, PipelineRun
- [ ] T012 Implement database initialization and async session factory in `packages/storage/src/hand2notes/storage/database.py` — SQLite engine, create-all, engine lifecycle with SQLModel
- [ ] T013 Generate initial Alembic migration from SQLModel tables in `apps/python-api/migrations/versions/001_initial_schema.py`
- [ ] T014 Implement FastAPI application entry point with lifespan, CORS, and router registration in `apps/python-api/src/hand2notes/api/main.py`
- [ ] T015 [P] Implement structured logging middleware and global error handlers in `apps/python-api/src/hand2notes/api/middleware.py` — request/response logging, pipeline error envelope
- [ ] T016 [P] Implement artifact registry service for tracking ExportArtifact records in `packages/storage/src/hand2notes/storage/artifact_registry.py`
- [ ] T017 Implement Electron main process: spawn Python API on random port, communicate port to renderer via IPC in `apps/electron-ui/src/main/index.ts`
- [ ] T018 [P] Implement Electron preload script with contextBridge for file-picker and OS-level operations in `apps/electron-ui/src/preload/index.ts`
- [ ] T019 [P] Initialize Zustand store structure with session, pipeline, and review slices in `apps/electron-ui/src/renderer/stores/index.ts`
- [ ] T020 Implement HTTP + WebSocket API client service for the Python backend in `apps/electron-ui/src/renderer/services/api.ts` — typed wrappers for all session, pipeline, and config endpoints

**Checkpoint**: Foundation ready — all user story phases can now proceed in order (or in parallel if staffed).

---

## Phase 3: User Story 1 — Import and Convert a Notebook Page (Priority: P1) 🎯 MVP

**Goal**: A user imports one or more notebook page photos; the system processes them through the full text pipeline (import → preprocess → layout → OCR → structure → export) and produces a readable Markdown note in the configured Obsidian vault folder.

**Independent Test**: Import a single JPEG with a title, two section headings, and a bullet list. Verify the exported `notes.md` appears in the vault folder with a `#` heading, `##` section headings, and a `- ` bullet list in the original reading order.

### Implementation

- [ ] T021 Implement image validation and format normalization in `packages/ingestion/src/hand2notes/ingestion/importer.py` — accept JPG, JPEG, PNG; validate file size (< 50 MB); record source_path, width_px, height_px on Page model
- [ ] T022 [P] Create golden OCR fixture: add `input.jpg` (handwritten page with heading, paragraph, bullet list) and `expected-text.md` to `tests/golden/ocr/mixed-heading-list/`
- [ ] T023 Implement deskew and perspective correction in `packages/preprocessing/src/hand2notes/preprocessing/deskew.py` — OpenCV Hough line detection, affine warp correction, output normalized image
- [ ] T024 [P] Implement denoising, shadow reduction, and contrast normalization in `packages/preprocessing/src/hand2notes/preprocessing/denoise.py` — OpenCV adaptiveThreshold, scikit-image background removal
- [ ] T025 Implement layout region detection in `packages/layout/src/hand2notes/layout/detector.py` — call Surya to produce list of `Block` with `BoundingBox`, `block_type`, and initial `confidence`
- [ ] T026 [P] Create golden layout fixture: add `input.jpg` and `expected-blocks.json` to `tests/golden/layout/engineering-notes-single-page/`
- [ ] T027 Implement reading order determination in `packages/layout/src/hand2notes/layout/reading_order.py` — use Surya to assign `reading_order` index to each block in non-linear layouts
- [ ] T028 Implement PaddleOCR adapter in `packages/ocr/src/hand2notes/ocr/paddle_adapter.py` — text extraction per block region with per-line confidence scores for Spanish and English
- [ ] T029 [P] Implement TrOCR handwriting fallback adapter in `packages/ocr/src/hand2notes/ocr/trocr_adapter.py` — triggered when PaddleOCR confidence < threshold for a block
- [ ] T030 [P] Implement Docling adapter in `packages/ocr/src/hand2notes/ocr/docling_adapter.py` — structured document backbone for Markdown-oriented extraction
- [ ] T031 Implement OCR orchestrator in `packages/ocr/src/hand2notes/ocr/orchestrator.py` — primary path: Docling + PaddleOCR; fallback: TrOCR per block below confidence threshold; sets `block.content` and `block.confidence`
- [ ] T032 Implement structure reconstructor in `packages/markdown_export/src/hand2notes/markdown_export/reconstructor.py` — maps `BlockType` to Markdown elements: `title` → `#`, `heading` → `##`/`###`, `paragraph` → plain text, `bullet_list` → `- `, `numbered_list` → `1. `; preserves reading order
- [ ] T033 Implement Markdown note renderer using Jinja2 in `packages/markdown_export/src/hand2notes/markdown_export/renderer.py` — concatenates reconstructed blocks into final Markdown string; inserts YAML front matter placeholder
- [ ] T034 Implement pipeline stage orchestrator for stages `import → preprocess → detect_layout → recognize_text → reconstruct_structure → generate_output` in `apps/python-api/src/hand2notes/pipeline/orchestrator.py` — async stage execution, PipelineRun creation, status transitions
- [ ] T035 [P] Implement PipelineRun logger in `packages/storage/src/hand2notes/storage/run_logger.py` — writes stage start/complete/fail to database, emits structured metrics dict
- [ ] T036 Implement session API router in `apps/python-api/src/hand2notes/api/routers/sessions.py` — `POST /sessions`, `POST /sessions/{id}/pages` (multipart), `GET /sessions`, `GET /sessions/{id}`, `PATCH /sessions/{id}`, `PATCH /sessions/{id}/pages/reorder`, `DELETE /sessions/{id}`
- [ ] T037 Implement pipeline API router skeleton in `apps/python-api/src/hand2notes/api/routers/pipeline.py` — `POST /sessions/{id}/process`, `POST /sessions/{id}/stages/{stage}`, `GET /sessions/{id}/runs/{run_id}`, `POST /sessions/{id}/runs/{run_id}/cancel`
- [ ] T038 Implement WebSocket progress endpoint `/sessions/{session_id}/progress` in `apps/python-api/src/hand2notes/api/routers/pipeline.py` — streams `stage_started`, `stage_completed`, `page_processed`, `block_detected`, `run_completed` JSON frames
- [ ] T039 Implement basic vault writer in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` — creates `<vault>/<notebook>/<session>/notes.md` with `diagrams/` and `assets/` subfolders; overwrite mode as default
- [ ] T040 [P] Implement Import page in `apps/electron-ui/src/renderer/pages/ImportPage.tsx` — file picker integration, image thumbnail list, drag-to-reorder page sequence, session metadata form (name, notebook, topic, tags), submit to `POST /sessions` + `POST /sessions/{id}/pages`
- [ ] T041 [P] Implement Processing page in `apps/electron-ui/src/renderer/pages/ProcessingPage.tsx` — stage progress bar, per-stage label, WebSocket progress stream, cancel button
- [ ] T042 Implement session store in `apps/electron-ui/src/renderer/stores/sessionStore.ts` — session object, pages list, current session ID, create/load/delete actions
- [ ] T043 [P] Implement pipeline store in `apps/electron-ui/src/renderer/stores/pipelineStore.ts` — current run ID, stage statuses, progress percent, cancel action
- [ ] T044 Wire Electron main process file-picker to Import page via contextBridge in `apps/electron-ui/src/main/file-picker.ts` — opens native system file dialog, returns selected paths to renderer
- [ ] T045 [P] Implement basic YAML front matter builder in `packages/markdown_export/src/hand2notes/markdown_export/front_matter.py` — generates `title`, `created`, `session`, `source_images`, `tags` fields for US1 export

**Checkpoint**: US1 complete and independently testable — import one JPEG page, run full pipeline, receive `notes.md` in the vault folder with recognizable Markdown structure.

---

## Phase 4: User Story 2 — Diagram Detection and Export (Priority: P2)

**Goal**: The pipeline detects diagram regions on notebook pages, classifies them (flowchart, sequence, UML, etc.), generates a PlantUML or draw.io source file, preserves the original crop, and embeds a reference link in the Markdown note.

**Independent Test**: Import a page with a clear flowchart. Verify a `.puml` file appears in `<vault>/<session>/diagrams/` and the exported `notes.md` contains an embed link (`![[diagram.puml]]`) at the correct reading order position.

### Implementation

- [ ] T046 Extend layout detector in `packages/layout/src/hand2notes/layout/detector.py` to classify regions as `block_type=diagram`; produce `DiagramBlock` with `crop_path` always set
- [ ] T047 [P] Create golden flowchart fixture: add `input.jpg` and `expected-plantuml.puml` to `tests/golden/diagrams/flowchart-basic/`
- [ ] T048 [P] Create golden sequence diagram fixture: add `input.jpg` and `expected-plantuml.puml` to `tests/golden/diagrams/sequence-diagram/`
- [ ] T049 Implement Ollama VLM client in `packages/diagrams/src/hand2notes/diagrams/vlm_client_ollama.py` — sends diagram crop to `qwen2.5vl:7b` via Ollama HTTP API, requests constrained JSON output (nodes, edges, type, confidence)
- [ ] T050 [P] Implement llama.cpp VLM client in `packages/diagrams/src/hand2notes/diagrams/vlm_client_llamacpp.py` — loads GGUF model via `llama-cpp-python`, same constrained JSON contract as Ollama client
- [ ] T051 Implement VLM response validator in `packages/diagrams/src/hand2notes/diagrams/vlm_validator.py` — parses constrained JSON into `DiagramNode` and `DiagramEdge` objects; assigns `reconstruction_confidence`; handles malformed output with fallback to `review_flag=True`
- [ ] T052 Implement PlantUML renderer in `packages/diagrams/src/hand2notes/diagrams/plantuml_renderer.py` — generates `.puml` source for `flowchart`, `sequence`, `uml_class`, `uml_activity`, `block_diagram`, `architecture` diagram types from validated nodes/edges
- [ ] T053 [P] Implement draw.io XML renderer in `packages/diagrams/src/hand2notes/diagrams/drawio_renderer.py` — generates `.drawio` XML for `annotated_sketch`, `graph_network`, and other free-form geometry types
- [ ] T054 Implement diagram crop saver in `packages/diagrams/src/hand2notes/diagrams/crop_saver.py` — always saves the cropped region image to `assets/` before any reconstruction attempt; sets `DiagramBlock.crop_path`
- [ ] T055 Add `detect_diagrams` stage to pipeline orchestrator in `apps/python-api/src/hand2notes/pipeline/orchestrator.py` — runs after `reconstruct_structure`; invokes VLM client selected by `VaultConfig.vlm_runtime`
- [ ] T056 Add diagram review endpoints to pipeline router in `apps/python-api/src/hand2notes/api/routers/pipeline.py` — `GET /sessions/{id}/pages/{pid}/review` (includes `diagram_previews`), `PATCH /sessions/{id}/pages/{pid}/diagrams/{bid}` (sets `review_decision`)
- [ ] T057 Update Markdown renderer in `packages/markdown_export/src/hand2notes/markdown_export/renderer.py` to embed diagram references — use `![[diagram.puml]]` for approved diagrams, `![crop](assets/crop.jpg)` for rejected or fallback
- [ ] T058 Update vault writer in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` to write `.puml` and `.drawio` files to `<session>/diagrams/`
- [ ] T059 [P] Implement DiagramPreview component in `apps/electron-ui/src/renderer/components/DiagramPreview.tsx` — shows crop image, diagram type label, reconstruction confidence badge, approve/reject/defer buttons
- [ ] T060 Implement config API router in `apps/python-api/src/hand2notes/api/routers/config.py` — `GET /config`, `PUT /config`, `PATCH /config`, `GET /config/vault/validate`, `GET /config/vlm/status`
- [ ] T061 [P] Implement config service in `apps/python-api/src/hand2notes/api/config_service.py` — loads/saves `~/.config/hand2notes/config.json`, validates vault path writability, checks VLM runtime availability
- [ ] T062 Extend artifact registry in `packages/storage/src/hand2notes/storage/artifact_registry.py` to record `ExportArtifact` entries for `.puml`, `.drawio`, and crop image files

**Checkpoint**: US2 complete and independently testable — pages with diagrams produce `.puml` or `.drawio` files and correct embed references in the Markdown note; unrecoverable diagrams preserve the crop with a review flag.

---

## Phase 5: User Story 5 — Obsidian Vault Export and Organization (Priority: P2)

**Goal**: The user configures an Obsidian vault root once. All exports go into a predictable folder structure (`<vault>/<notebook>/<session>/notes.md`) with YAML front matter and Obsidian-compatible embed links. Overwrite, versioned, and merge export modes all work correctly.

**Independent Test**: Configure a test vault folder, process one page, export it. Open the vault in Obsidian; verify the note appears with correct YAML front matter (title, date, tags, source images), a `##` heading, and a working `![[diagram.puml]]` embed link.

### Implementation

- [ ] T063 Implement VaultConfig persistence in `packages/storage/src/hand2notes/storage/vault_config.py` — load/save JSON at `~/.config/hand2notes/config.json`; expose typed `VaultConfig` model
- [ ] T064 Implement Jinja2 folder template engine in `packages/markdown_export/src/hand2notes/markdown_export/folder_template.py` — renders `{{notebook}}/{{date}}-{{topic}}` template with session fields; validates Jinja2 syntax on save
- [ ] T065 Implement full YAML front matter builder in `packages/markdown_export/src/hand2notes/markdown_export/front_matter.py` — generates `title`, `date`, `session`, `notebook`, `topic`, `tags`, `source_images`, `confidence_summary`, and custom `front_matter_fields` from `VaultConfig`; uses `python-frontmatter`
- [ ] T066 Implement overwrite export mode in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` — replaces existing `notes.md` and all companion files without creating duplicates; verifies no stale files remain
- [ ] T067 [P] Implement versioned export mode in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` — writes `notes-{timestamp}.md` alongside existing versions without touching prior exports
- [ ] T068 [P] Implement merge export mode in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` — appends new pages to existing `notes.md` without replacing content from prior exports
- [ ] T069 Implement export endpoints in `apps/python-api/src/hand2notes/api/routers/pipeline.py` — `POST /sessions/{id}/export` (triggers vault write, returns 202), `GET /sessions/{id}/export/status` (returns artifact list and write status)
- [ ] T070 Implement Obsidian embed syntax for all artifact types in `packages/markdown_export/src/hand2notes/markdown_export/renderer.py` — `![[diagram.puml]]` for PlantUML, `![[diagram.drawio]]` for draw.io, `![[image.jpg]]` for asset images
- [ ] T071 Implement vault validation logic in `apps/python-api/src/hand2notes/api/config_service.py` — checks path exists, is a directory, is writable, counts existing `.md` files; returns structured response for `GET /config/vault/validate`
- [ ] T072 [P] Implement Settings page in `apps/electron-ui/src/renderer/pages/SettingsPage.tsx` — vault root path picker, folder template input, export mode selector (overwrite/versioned/merge), VLM runtime selector, VLM model field, vault validation status display
- [ ] T073 Implement Export confirmation page in `apps/electron-ui/src/renderer/pages/ExportPage.tsx` — export mode selector, submit to `POST /sessions/{id}/export`, progress display, artifact list on completion with vault-relative paths

**Checkpoint**: US5 complete and independently testable — vault path configured, correct folder structure created, front matter valid, all three export modes produce expected output, existing vault notes untouched.

---

## Phase 6: User Story 6 — Review and Correction Workflow (Priority: P2)

**Goal**: Before final export, the app presents a review screen with the original image alongside extracted text blocks, confidence indicators, Markdown preview, and diagram previews. The user can correct text, approve/reject diagrams, and resolve flagged regions before confirming export.

**Independent Test**: Process a page that has one low-confidence OCR region and one diagram. Verify the review screen shows the confidence warning on the flagged block, allows inline text correction, shows the diagram preview with approve/reject controls, and blocks export until the user confirms.

### Implementation

- [ ] T074 Implement review payload builder in `packages/review/src/hand2notes/review/review_builder.py` — assembles `GET /review` response: original image URL, preprocessed image URL, blocks with all fields, Markdown preview string, diagram previews list, overall confidence
- [ ] T075 Implement confidence threshold flagging in `packages/review/src/hand2notes/review/confidence_flagging.py` — sets `block.review_flag=True` for any block with `confidence < config.confidence_threshold` (default 0.65); also flags blocks with `content=None`
- [ ] T076 Implement block correction service in `packages/review/src/hand2notes/review/correction_service.py` — writes `corrected_content` to block, clears `review_flag`, updates `review_status` on parent page, persists to database
- [ ] T077 Add block correction endpoint to pipeline router in `apps/python-api/src/hand2notes/api/routers/pipeline.py` — `PATCH /sessions/{id}/pages/{pid}/blocks/{bid}` with `corrected_content` and `review_flag` fields; returns updated Block
- [ ] T078 Add review page endpoint to pipeline router in `apps/python-api/src/hand2notes/api/routers/pipeline.py` — `GET /sessions/{id}/pages/{pid}/review`; delegates to `review_builder`
- [ ] T079 Serve static image crops via FastAPI in `apps/python-api/src/hand2notes/api/main.py` — mount `/static/crops/` to the preprocessing output directory; also serve generated artifact previews
- [ ] T080 [P] Implement Review page layout in `apps/electron-ui/src/renderer/pages/ReviewPage.tsx` — split-panel: left = original + preprocessed image; right = block list with confidence badges, Markdown preview panel, diagram previews; navigation between pages in session
- [ ] T081 [P] Implement ConfidenceBadge component in `apps/electron-ui/src/renderer/components/ConfidenceBadge.tsx` — renders colored badge (green/yellow/red) based on confidence score; highlights flagged blocks with warning icon
- [ ] T082 Implement inline block text editor in `apps/electron-ui/src/renderer/components/BlockEditor.tsx` — editable textarea pre-filled with `content` or `corrected_content`; PATCH on blur; clears review flag indicator on save
- [ ] T083 [P] Implement Markdown preview panel in `apps/electron-ui/src/renderer/components/MarkdownPreview.tsx` — renders `markdown_preview` string using `markdown-it`; updates live as user corrects blocks
- [ ] T084 Implement diagram review controls in `apps/electron-ui/src/renderer/components/DiagramReviewControls.tsx` — approve/reject/defer buttons; sends `PATCH /sessions/{id}/pages/{pid}/diagrams/{bid}`; updates `DiagramPreview` state
- [ ] T085 Implement review store in `apps/electron-ui/src/renderer/stores/reviewStore.ts` — current page review data, correction drafts, diagram decisions, review completion check, navigate-to-next-page action

**Checkpoint**: US6 complete and independently testable — review screen functional, flagged blocks highlighted, text corrections persisted, diagram decisions recorded, export only proceeds after user confirmation.

---

## Phase 7: User Story 3 — Table Reconstruction (Priority: P3)

**Goal**: The pipeline detects hand-drawn tables, reconstructs them as Markdown tables. When a table cannot be reliably reconstructed, the system exports a CSV or image crop fallback referenced from the note.

**Independent Test**: Import a page with a clearly drawn 3×3 table with column headers and 3 rows. Verify the exported `notes.md` contains a Markdown table with correct headers, row data, and column alignment.

### Implementation

- [ ] T086 Implement table region detector in `packages/tables/src/hand2notes/tables/detector.py` — identifies `block_type=table` regions in layout output using horizontal/vertical line detection (OpenCV)
- [ ] T087 [P] Create golden table fixture: add `input.jpg` (3×3 table with headers) and `expected-markdown.md` to `tests/golden/tables/simple-3x3/`
- [ ] T088 Implement table cell extraction and grid reconstruction in `packages/tables/src/hand2notes/tables/cell_extractor.py` — OpenCV line grid detection, cell bounding boxes, OCR per cell using `ocr.orchestrator`, builds `TableBlock.headers` and `TableBlock.rows`
- [ ] T089 Implement Markdown table renderer in `packages/tables/src/hand2notes/tables/md_renderer.py` — produces GFM-compatible `| col | col |` format with `|---|---|` separator row; left-aligns all columns by default
- [ ] T090 [P] Implement CSV fallback exporter in `packages/tables/src/hand2notes/tables/csv_fallback.py` — writes `table-{n}.csv` to `assets/` when `reconstruction_confidence < 0.5`; sets `TableBlock.fallback_type=csv` and `fallback_path`
- [ ] T091 Implement table caption detection in `packages/tables/src/hand2notes/tables/caption_detector.py` — reads the nearest text block above the table region; assigns to `TableBlock.caption`
- [ ] T092 [P] Implement image crop fallback for tables in `packages/tables/src/hand2notes/tables/image_fallback.py` — saves crop image to `assets/` when table is too irregular for either Markdown or CSV; sets `fallback_type=image`
- [ ] T093 Add table detection and reconstruction as a sub-step of `reconstruct_structure` stage in `apps/python-api/src/hand2notes/pipeline/orchestrator.py` — processes `block_type=table` blocks through `tables.cell_extractor` before structure reconstruction
- [ ] T094 Update Markdown renderer in `packages/markdown_export/src/hand2notes/markdown_export/renderer.py` to handle `TableBlock` — outputs Markdown table when `reconstruction_confidence >= 0.5`; outputs `![table](assets/table-n.csv)` or image embed for fallback cases; prepends caption if present
- [ ] T095 Update vault writer in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` to copy CSV and table crop files to `<session>/assets/`
- [ ] T096 [P] Implement TablePreview component in `apps/electron-ui/src/renderer/components/TablePreview.tsx` — renders HTML table preview in Review page; shows reconstruction confidence badge; links to CSV fallback if present
- [ ] T097 Extend artifact registry in `packages/storage/src/hand2notes/storage/artifact_registry.py` to record `ExportArtifact` entries for table CSV and image fallback files

**Checkpoint**: US3 complete and independently testable — 3×3 table page produces valid Markdown table; unrecoverable table produces CSV or image crop fallback referenced from the note; no table is silently dropped.

---

## Phase 8: User Story 4 — Visual Semantics and Highlights (Priority: P3)

**Goal**: The pipeline detects visual emphasis (highlights, underlines, boxes, callout arrows, color coding) and handwritten URLs, preserving them in the Markdown output using Obsidian-compatible notation.

**Independent Test**: Import a page with a highlighted passage, a boxed callout, and a written URL. Verify the output uses `==text==` for the highlight, `> [!NOTE]` for the boxed callout, and `[text](url)` for the URL.

### Implementation

- [ ] T098 Implement highlight color detection in `packages/preprocessing/src/hand2notes/preprocessing/highlight_detector.py` — HSV color space analysis (OpenCV) to identify highlighted regions; returns color name/hex and bounding regions
- [ ] T099 [P] Implement underline, box, and circle shape detection in `packages/preprocessing/src/hand2notes/preprocessing/shape_detector.py` — OpenCV contour analysis; distinguishes underlines from boxes from circles; sets `VisualSemantics.is_underlined`, `is_boxed`, `is_circled`
- [ ] T100 Implement visual semantics mapper in `packages/layout/src/hand2notes/layout/semantics_mapper.py` — associates detected highlights/shapes with overlapping text blocks; populates `Block.visual_semantics` with `VisualSemantics` model
- [ ] T101 Implement Obsidian highlight renderer in `packages/markdown_export/src/hand2notes/markdown_export/semantics_renderer.py` — wraps highlighted text with `==text==` notation when `VisualSemantics.highlight_color` is set
- [ ] T102 [P] Implement Obsidian callout block renderer in `packages/markdown_export/src/hand2notes/markdown_export/semantics_renderer.py` — wraps boxed/circled regions with `> [!NOTE]\n> content` using `VisualSemantics.callout_label` as the callout type when available
- [ ] T103 Implement handwritten URL detector in `packages/ocr/src/hand2notes/ocr/url_detector.py` — regex pattern matching on OCR output to identify URL-like strings (`http://`, `www.`, `.com` patterns); assigns `block_type=url_reference`; sets `confidence` based on OCR clarity
- [ ] T104 Implement Markdown hyperlink formatter in `packages/markdown_export/src/hand2notes/markdown_export/url_formatter.py` — renders detected URLs as `[url](url)` or `<url>` in Markdown output
- [ ] T105 Extend front matter builder in `packages/markdown_export/src/hand2notes/markdown_export/front_matter.py` to include color semantic metadata — adds `color_annotations` list to YAML front matter when `VisualSemantics.highlight_color` is set on any block
- [ ] T106 Add visual semantics detection as a sub-step between `recognize_text` and `reconstruct_structure` in `apps/python-api/src/hand2notes/pipeline/orchestrator.py` — runs `semantics_mapper`, `highlight_detector`, `shape_detector`, and `url_detector` per page
- [ ] T107 Update Markdown renderer in `packages/markdown_export/src/hand2notes/markdown_export/renderer.py` to apply `VisualSemantics` when rendering each block — delegates to `semantics_renderer` and `url_formatter` before concatenating block content
- [ ] T108 [P] Implement visual semantics indicators in BlockEditor in `apps/electron-ui/src/renderer/components/BlockEditor.tsx` — show highlight color swatch, underline/box/circle icons, and URL link icon alongside flagged blocks in Review page
- [ ] T109 Update review endpoint in `apps/python-api/src/hand2notes/api/routers/pipeline.py` to include `visual_semantics` object in each block payload of `GET /sessions/{id}/pages/{pid}/review`

**Checkpoint**: US4 complete and independently testable — page with highlights, callouts, and URLs produces Markdown output with `==highlight==`, `> [!NOTE]` callouts, and `[url](url)` links; color metadata appears in YAML front matter.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, performance, full end-to-end validation, and coverage of edge cases that span all user stories.

- [ ] T110 [P] Add structured error responses (RFC 7807 problem+json) for all pipeline failure modes across all API routers in `apps/python-api/src/hand2notes/api/middleware.py`
- [ ] T111 [P] Implement HEIC to JPEG conversion at ingestion stage in `packages/ingestion/src/hand2notes/ingestion/importer.py` — add Pillow HEIF plugin dependency; convert before downstream processing
- [ ] T112 Add cancellation signal propagation to every pipeline stage in `apps/python-api/src/hand2notes/pipeline/orchestrator.py` — honour asyncio `CancelledError` in each stage's processing loop; update PipelineRun status to `cancelled`
- [ ] T113 [P] Emit per-stage metrics in `packages/storage/src/hand2notes/storage/run_logger.py` — `blocks_detected`, `confidence_mean`, `pages_processed` per stage; expose in `GET /sessions/{id}/runs/{run_id}` response
- [ ] T114 [P] Add progress streaming for batch sessions (20+ pages) in `apps/python-api/src/hand2notes/api/routers/pipeline.py` WebSocket — emit `page_processed` events with `current_page` / `total_pages` count per page completed
- [ ] T115 Implement stale file cleanup for overwrite mode in `packages/markdown_export/src/hand2notes/markdown_export/vault_writer.py` — scan `<session>/` folder before write; remove files from prior export that are not in the current artifact list
- [ ] T116 [P] Add per-stage timing instrumentation in `apps/python-api/src/hand2notes/pipeline/orchestrator.py` — log elapsed time per stage to PipelineRun.metrics; warn if cumulative time exceeds 90 s threshold
- [ ] T117 [P] Add Electron tray icon and window management in `apps/electron-ui/src/main/tray.ts` — system tray icon with show/hide window, quit action
- [ ] T118 Run full quickstart.md validation: `uv sync`, `alembic upgrade head`, `uvicorn` dev server, `pnpm install`, `pnpm dev` — confirm all commands succeed from a clean checkout
- [ ] T119 [P] Add integration test using a sample page from `samples/` directory: create session → upload → process → review → export; assert `notes.md` exists in configured test vault path
- [ ] T120 Update `docs/` with architecture overview, monorepo structure guide, and pointer to `specs/001-handwritten-to-obsidian/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — MVP increment; must complete before US2 and US5 can fully integrate
- **US2 (Phase 4)**: Depends on Phase 2; integrates with US1 pipeline stages
- **US5 (Phase 5)**: Depends on Phase 2; integrates with US1 vault writer
- **US6 (Phase 6)**: Depends on Phase 2; depends on US1 (review requires extracted blocks); integrates with US2 diagram review
- **US3 (Phase 7)**: Depends on Phase 2; integrates with US1 layout and OCR stages
- **US4 (Phase 8)**: Depends on Phase 2; integrates with US1 OCR and renderer stages
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

| Story | Depends on Phases | Independent? |
|-------|------------------|--------------|
| US1 (P1) | Phase 1 + 2 | Yes — fully self-contained |
| US2 (P2) | Phase 1 + 2 + US1 pipeline stages | Integration only — diagram stage slots into existing pipeline |
| US5 (P2) | Phase 1 + 2 + US1 vault writer | Integration only — extends vault_writer |
| US6 (P2) | Phase 1 + 2 + US1 blocks | Integration only — review payload needs extracted blocks |
| US3 (P3) | Phase 1 + 2 + US1 layout/OCR | Integration only — table stage slots into pipeline |
| US4 (P3) | Phase 1 + 2 + US1 OCR/renderer | Integration only — semantics stage slots into pipeline |

### Within Each User Story

- Models before services
- Services before API endpoints
- API endpoints before UI integration
- Golden fixtures before pipeline stage implementation (constitution Principle V)
- Story complete before moving to next priority

---

## Parallel Opportunities

### Phase 3 (US1 — MVP) Parallel Groups

```
Group A (run together): T022 T023 T024 T026 T029 T030 T035 T040 T041 T043 T044 T045
Group B (after T025): T027 T028
Group C (after T028, T031): T032 T033
Group D (after T032, T033): T034
```

### Phase 4 (US2) Parallel Groups

```
Group A (run together): T047 T048 T050 T053 T054 T059 T061
Group B (after T049, T050, T051): T052 T053
```

### Phase 5 (US5) Parallel Groups

```
Group A (run together): T067 T068 T072
```

### Phase 6 (US6) Parallel Groups

```
Group A (run together): T080 T081 T083 T084
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T007)
2. Complete Phase 2: Foundational (T008–T020) — **CRITICAL, blocks everything**
3. Complete Phase 3: User Story 1 (T021–T045)
4. **STOP and VALIDATE**: Import one JPEG page → process → review → export to test vault → open in Obsidian
5. Demo if ready; ship as MVP

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Phase 3 (US1) → Basic text pipeline works → **MVP demo**
3. Phase 4 (US2) → Diagram pipeline works → export diagrams to vault
4. Phase 5 (US5) → Full vault organization + all export modes
5. Phase 6 (US6) → Review screen gates all exports
6. Phase 7 (US3) → Tables reconstructed
7. Phase 8 (US4) → Visual semantics + URLs
8. Phase 9 → Polish, hardening, final validation

### Parallel Team Strategy (3 developers after Phase 2)

- **Dev A**: US1 (Phase 3) — core text pipeline and basic Electron UI
- **Dev B**: US2 (Phase 4) + US5 (Phase 5) — diagram pipeline and vault organization
- **Dev C**: US6 (Phase 6) — review/correction workflow UI

---

## Notes

- `[P]` tasks operate on different files with no cross-task dependencies at the time they are marked parallel
- `[Story]` label maps each task to its user story for traceability and scoping
- Each user story phase is independently completable and testable before moving to the next
- Golden fixtures (T022, T026, T047, T048, T087) must be created **before** implementing the corresponding pipeline stage (constitution Principle V)
- Commit after each task or logical group; stop at any `Checkpoint` to validate the story independently
- VLM setup (Ollama or llama.cpp) is required before implementing Phase 4 (US2)
- The `confidence_threshold` (default 0.65) is the key tunable for balancing automation vs. review burden
