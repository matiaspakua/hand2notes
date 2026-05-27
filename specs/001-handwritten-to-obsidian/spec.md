# Feature Specification: Handwritten Notes to Obsidian Vault

**Feature Branch**: `001-handwritten-to-obsidian`

**Created**: 2026-05-27

**Status**: Draft

**Input**: Convert handwritten notebook page images into structured Markdown notes and store them in an Obsidian vault knowledge base, preserving diagrams, tables, visual semantics, highlights, and web references.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Import and Convert a Notebook Page (Priority: P1)

A user photographs one or more handwritten notebook pages on their phone and imports them into the desktop application. The system processes the pages and produces a clean, readable Markdown note with correct reading order, headings, paragraphs, bullet lists, and numbered lists. The note is exported directly into a configured Obsidian vault folder.

**Why this priority**: This is the core value proposition of the application. Every other feature depends on getting this right. Without it, nothing else matters.

**Independent Test**: Can be fully tested by importing a single page with mixed headings, paragraphs, and a list, then verifying the exported Markdown note appears in the vault folder with recognizable structure.

**Acceptance Scenarios**:

1. **Given** a JPEG photo of a handwritten page with a title, two sections, and a bullet list, **When** the user imports it and triggers processing, **Then** the system exports a Markdown file in the vault folder with a heading, section headings, and a proper bullet list in the original reading order.
2. **Given** a batch of three ordered notebook page photos, **When** processed as a session, **Then** the system exports a single Markdown note (or one per page per user choice) with pages in the correct order and each page clearly demarcated.
3. **Given** a photo with poor lighting or slight skew, **When** processed, **Then** the system applies preprocessing and extracts usable text, or flags low-confidence regions for review rather than silently dropping them.

---

### User Story 2 — Diagram Detection and Export (Priority: P2)

A notebook page contains a hand-drawn diagram (flowchart, architecture diagram, UML sequence, block diagram). The system detects the diagram region, classifies its type, and generates an editable diagram source file. The Markdown note references the diagram. The original diagram crop is preserved for traceability.

**Why this priority**: Handwritten engineering notes frequently contain diagrams. Producing only text from a diagram-heavy page delivers incomplete value.

**Independent Test**: Can be tested by importing a page containing a clear flowchart, then verifying a `.puml` or `.drawio` file is generated and referenced in the Markdown output.

**Acceptance Scenarios**:

1. **Given** a page with a hand-drawn flowchart, **When** processed, **Then** the system detects the diagram region, generates a PlantUML or draw.io source file in the `diagrams/` folder, and inserts a reference link in the Markdown note.
2. **Given** a diagram the system cannot reconstruct reliably, **When** processed, **Then** the system preserves the cropped diagram image, inserts a placeholder in the Markdown with a manual-review flag, and does not silently omit it.
3. **Given** a page with multiple diagrams, **When** processed, **Then** each diagram is extracted and referenced independently in reading order.

---

### User Story 3 — Table Reconstruction (Priority: P3)

A notebook page contains a hand-drawn table with headers and rows. The system reconstructs the table into Markdown table format. When a table cannot be reliably reconstructed, a CSV fallback or image crop is preserved and referenced.

**Why this priority**: Tables are a common and high-value structure in study and engineering notes. Losing table structure significantly reduces note quality.

**Independent Test**: Can be tested by importing a page with a clearly drawn 3×3 table with headers, then verifying the exported Markdown note contains a properly formatted Markdown table.

**Acceptance Scenarios**:

1. **Given** a page with a legible hand-drawn table with column headers and 3 rows, **When** processed, **Then** the Markdown note contains a Markdown table with correct headers, rows, and column alignment.
2. **Given** a table too irregular to reconstruct reliably, **When** processed, **Then** the system exports a CSV or image fallback, references it from the note, and marks it for review.
3. **Given** a table with a visible caption written above it, **When** processed, **Then** the caption appears as a label above the table in the Markdown output.

---

### User Story 4 — Visual Semantics and Highlights (Priority: P3)

A notebook page uses visual emphasis: highlighted passages, circled words, underlines, boxed sections, callout arrows, and color-coded sections. The system preserves these semantics using Markdown-compatible or Obsidian-compatible notation. URLs or web references written on the page are recognized and formatted as Markdown hyperlinks.

**Why this priority**: Visual emphasis carries meaning in engineering and study notes. Losing it produces notes that look complete but miss key signals the author considered important.

**Independent Test**: Can be tested by importing a page with at least one highlighted passage, one boxed callout, and one written URL, then verifying the output uses bold/highlight markers, a blockquote or callout block, and a formatted hyperlink.

**Acceptance Scenarios**:

1. **Given** a passage highlighted with a marker pen, **When** processed, **Then** the text appears with Obsidian-compatible highlight markup (`==text==`) or bold in the Markdown output.
2. **Given** a web URL written in handwriting on the page, **When** processed, **Then** the URL is recognized as a hyperlink and formatted as `[text](url)` or `<url>` in the Markdown output.
3. **Given** a boxed region with a callout label, **When** processed, **Then** the content is represented as an Obsidian callout block (`> [!NOTE]`) or equivalent Markdown blockquote in the output.
4. **Given** a color-coded section (e.g., red underline for warnings, green for key concepts), **When** processed, **Then** the color semantic is preserved in metadata or via Obsidian tag notation even if inline color rendering is not possible.

---

### User Story 5 — Obsidian Vault Export and Organization (Priority: P2)

The user configures their Obsidian vault root folder once. The system exports all notes into a predictable, Obsidian-compatible folder structure with YAML front matter metadata. Notes are organized by notebook, course, or session. The vault structure is browsable and searchable in Obsidian immediately after export.

**Why this priority**: The Obsidian vault is the intended final home for all notes. Correct vault structure and metadata make the notes immediately useful in the knowledge base.

**Independent Test**: Can be tested by configuring a test vault folder, processing one page, then opening the vault in Obsidian and verifying the note appears with correct front matter, title, tags, and internal links to generated diagrams.

**Acceptance Scenarios**:

1. **Given** a configured vault path and a processed note session, **When** exported, **Then** the note appears at `<vault>/<notebook>/<session>/notes.md` with YAML front matter containing title, date, tags, and source image references.
2. **Given** a note with generated diagram files, **When** exported, **Then** the Markdown note contains Obsidian-compatible embed links (`![[diagram.puml]]` or image embeds) pointing to files in the same session folder.
3. **Given** a repeated export of the same session, **When** the user chooses the overwrite mode, **Then** the existing note is replaced cleanly without creating duplicate files; when versioned mode is chosen, a new timestamped version is created.
4. **Given** an Obsidian vault already containing notes, **When** a new export is added, **Then** existing notes and vault structure are not modified or corrupted.

---

### User Story 6 — Review and Correction Workflow (Priority: P2)

Before final export, the application presents a review screen showing the original image alongside the extracted text blocks, structural regions, Markdown preview, and generated diagram previews. Confidence warnings highlight uncertain sections. The user can correct text, approve or reject diagram reconstructions, and confirm before export.

**Why this priority**: Automated extraction is imperfect. A review step is the quality gate that prevents bad output from polluting the knowledge base.

**Independent Test**: Can be tested by processing a page with at least one low-confidence region and verifying the review screen shows the confidence warning, the original image, and allows text correction before export.

**Acceptance Scenarios**:

1. **Given** a processed page with one low-confidence OCR region, **When** the review screen is shown, **Then** the region is highlighted with a visual confidence indicator and the user can edit the extracted text inline.
2. **Given** a generated diagram, **When** the review screen is shown, **Then** the user can approve the diagram (include in export), reject it (replace with cropped image fallback), or defer it (mark as needs-manual-edit).
3. **Given** the user approves all regions in review, **When** they confirm export, **Then** the export runs and the note appears in the vault within a reasonable time with no additional prompts.

---

### Edge Cases

- What happens when an image is completely unreadable (blurry, dark, extreme distortion)?
- How does the system handle a page that is entirely a diagram with no text?
- What happens when a URL written on the page is partially legible or broken?
- How does the system handle multiple languages on the same page?
- What happens if the Obsidian vault path is on a network drive or cloud-synced folder that is temporarily unavailable?
- How are very long sessions (20+ pages) handled in terms of progress and cancellation?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept single images, batches of images, and full folder imports of notebook page photographs.
- **FR-002**: The system MUST support JPG, JPEG, PNG, and HEIC input formats at minimum.
- **FR-003**: The system MUST allow the user to define and reorder the page sequence before processing.
- **FR-004**: The system MUST preprocess images to correct common capture issues: deskewing, dewarping, denoising, shadow reduction, contrast normalization, and perspective correction.
- **FR-005**: The system MUST detect and reconstruct the following structural elements when present: titles, headings, paragraphs, bullet lists, numbered lists, tables, diagrams, callouts, marginal notes, arrows, and highlighted passages.
- **FR-006**: The system MUST determine reading order across arbitrary page layouts and preserve it in the output.
- **FR-007**: The system MUST extract handwritten text from notebook images with support for Spanish and English.
- **FR-008**: The system MUST provide block-level and line-level confidence scores for all extracted content.
- **FR-009**: The system MUST preserve uncertain fragments with an explicit review flag rather than silently discarding them.
- **FR-010**: The system MUST reconstruct note content into Markdown preserving: heading hierarchy, bullets, numbered lists, tables, code blocks, callouts, emphasized text, and internal diagram references.
- **FR-011**: The system MUST reconstruct hand-drawn tables as Markdown tables when structurally recoverable; it MUST fall back to CSV or image export with a Markdown reference when not.
- **FR-012**: The system MUST detect diagram regions and classify them by type (flowchart, sequence, UML, block, architecture, graph, annotated sketch, chart).
- **FR-013**: The system MUST generate a PlantUML source file for structured text-definable diagrams and a draw.io XML file for free-form geometry-heavy diagrams.
- **FR-014**: The system MUST preserve original cropped diagram images for traceability regardless of whether reconstruction succeeds.
- **FR-015**: The system MUST recognize handwritten URLs and format them as Markdown hyperlinks in the output note.
- **FR-016**: The system MUST represent visual semantics (highlights, underlines, boxed regions, color coding) using Obsidian-compatible Markdown notation or YAML metadata where direct rendering is not possible.
- **FR-017**: The system MUST allow the user to configure a destination Obsidian vault folder.
- **FR-018**: The system MUST export notes into a predictable vault folder structure: `<vault>/<notebook>/<session>/notes.md` with companion `diagrams/` and `assets/` subfolders.
- **FR-019**: The system MUST generate YAML front matter for every exported note, including: title, creation date, source image references, session name, tags, and confidence summary.
- **FR-020**: The system MUST support export modes: overwrite, versioned (timestamped), and merge (add new pages without replacing existing).
- **FR-021**: The system MUST present a review screen before final export, showing the original image, extracted regions, Markdown preview, diagram previews, and confidence warnings.
- **FR-022**: The system MUST allow the user to correct extracted text, approve or reject diagram reconstructions, and resolve flagged low-confidence regions in the review screen.
- **FR-023**: The system MUST support grouping pages into a named note session, with one Markdown file per session or one per page as a user-selectable option.
- **FR-024**: The system MUST show progress indicators, stage labels, and cancellation support for all long-running pipeline operations.
- **FR-025**: The system MUST emit structured logs and structured error details for all pipeline stages.

### Key Entities

- **Session**: An ordered collection of notebook page images belonging to one note-taking event (e.g., a class, a meeting, a study block). Carries notebook name, date, topic, and export settings.
- **Page**: A single notebook page image and all data derived from it. Carries source image path, preprocessing result, extracted blocks, confidence scores, and review status.
- **Block**: A detected region on a page with a type (text, table, diagram, callout, image). Carries bounding coordinates, content, confidence score, and review flag.
- **Table**: A structured block reconstructed into rows and columns. Carries headers, cell data, caption, reconstruction confidence, and fallback file reference.
- **Diagram**: A visual block classified by diagram type. Carries type classification, generated source file path, original crop path, node/edge data, reconstruction confidence, and review status.
- **ExportArtifact**: One generated output file (Markdown note, PlantUML file, draw.io file, CSV, image asset). Carries file path, type, and the session/page it belongs to.
- **VaultConfig**: The user's configured Obsidian vault settings: root path, default folder structure template, export mode preference, and front matter field mappings.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can import a batch of notebook page photos and receive a complete, exported Markdown note in their Obsidian vault within a time that makes the workflow practical for daily note digitization (a single standard page processed end-to-end in under 2 minutes on a modern laptop).
- **SC-002**: For pages with clear handwriting and standard note structure (headings, paragraphs, lists), the generated Markdown note achieves 80% or higher structural similarity to the original page as judged by a human reviewer.
- **SC-003**: Every detected diagram on a page results in either a generated editable source file or a preserved image crop with a review flag — no diagram is silently lost.
- **SC-004**: Every detected table on a page results in either a Markdown table, a CSV export, or a cropped image fallback — no table is silently lost.
- **SC-005**: Every exported note opens correctly in Obsidian with valid front matter, readable Markdown, and working internal links to generated diagram and asset files.
- **SC-006**: URLs written on notebook pages are recognized and formatted as functional hyperlinks in at least 70% of clearly legible handwritten URL cases.
- **SC-007**: A user with no prior configuration can complete the full workflow (import → process → review → export to vault) for a single page without consulting documentation.
- **SC-008**: Repeated exports of the same session in overwrite mode produce exactly one note file per session in the vault, with no duplicate files accumulating.

---

## Assumptions

- Users are capturing notebook photos with a modern smartphone (2018 or later); extreme image quality degradation (severe motion blur, extreme darkness) is out of scope for guaranteed recognition but handled with fallback flagging.
- The Obsidian vault is located on a locally accessible filesystem path (local drive or always-mounted network share); cloud-sync latency is the user's responsibility.
- Spanish and English are the two supported languages for text recognition in the first release; additional languages are architecturally possible but not in scope.
- The application runs entirely offline; no notebook content is sent to external services by default.
- Users are expected to review and correct generated output before considering it final; 100% automated accuracy is not promised.
- Obsidian-compatible highlight syntax (`==text==`), callout blocks (`> [!NOTE]`), and YAML front matter are the target notation for Obsidian-specific formatting.
- The first release targets desktop platforms (macOS, Windows, Linux); mobile capture from within the app is out of scope.
- Multi-page sessions produce a folder-based export; very large sessions (100+ pages) may require progress feedback but are within scope.
