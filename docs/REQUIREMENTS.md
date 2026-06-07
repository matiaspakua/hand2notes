# hand2notes Requirements

## 1. Purpose

hand2notes shall convert one or more mobile phone images of handwritten notebook pages into structured digital notes stored as Markdown files, plus companion diagram files when diagrams are detected.

The system shall preserve, as closely as possible, the original page semantics, reading order, section structure, hierarchy, tables, diagrams, emphasis, colors, and layout intent.

The target fidelity for the generated note shall be 80% to 90% similarity to the original notebook page, recognizing that Markdown has format limitations compared with free-form paper.

## 2. Product Scope

### 2.1 Input

The system shall accept:
- Single images and batches of images.
- Mobile phone photographs of notebook pages.
- Common raster formats, at minimum: JPG, JPEG, PNG, HEIC.
- Multi-page note sessions represented as ordered image sets.

### 2.2 Output

The system shall generate:
- One or more Markdown files representing the extracted notes.
- Companion diagram source files for recognized diagrams.
- Companion assets folder for cropped figures, tables, or images when needed.
- Structured metadata describing confidence, provenance, and reconstruction decisions.

### 2.3 Primary Use Cases

- Class or master session note digitization.
- Engineering notebook archival.
- Conversion of handwritten notes with diagrams and tables into editable knowledge-base content.
- Storage of generated notes inside a user-selected notes folder, grouped by notebook, course, session, or topic.

## 3. Functional Requirements

### 3.1 Ingestion

- The desktop app shall allow users to import one image, many images, or a full folder.
- The app shall preserve user-defined ordering of pages.
- The app shall support drag and drop and file-picker import.
- The app shall store the original images as source references or keep resolvable links to them.
- The app shall support assigning imported pages to a project, notebook, course, session, or folder.

### 3.2 Preprocessing

- The backend shall perform image preprocessing before OCR.
- Preprocessing shall include, when applicable: deskewing, dewarping, denoising, shadow reduction, contrast normalization, border cleanup, perspective correction, color normalization, and page boundary detection.
- The preprocessing pipeline shall preserve handwriting strokes and color cues relevant to semantic reconstruction.
- The system shall support per-image preprocessing previews for debugging and tuning.

### 3.3 Document Understanding

- The backend shall detect page structure before final content generation.
- The system shall identify at minimum the following regions when present:
  - titles
  - headings
  - paragraphs
  - bullet or numbered lists
  - tables
  - diagrams
  - formulas
  - labels/callouts
  - marginal notes
  - arrows and connectors
  - embedded images or sketches
- The system shall determine reading order across arbitrary page layouts.
- The system shall maintain line grouping, paragraph grouping, and section hierarchy.

### 3.4 Handwriting Recognition

- The backend shall extract handwritten text from notebook images.
- The OCR pipeline shall support mixed content pages containing handwriting, printed text, and symbols.
- The OCR pipeline shall support Spanish and English initially, with architecture ready for additional languages.
- The system shall provide block-level and line-level confidence scores.
- The system shall preserve uncertain fragments and mark them explicitly instead of silently dropping them.
- The system shall allow optional human correction before export.

### 3.5 Post-OCR Text Correction

- After OCR, the backend shall run a spell-correction pass on all text-bearing blocks (paragraphs, headings, bullet lists, numbered lists, callouts, marginal notes).
- The spell corrector shall support Spanish (`es`) and English (`en`) dictionaries. Additional languages may be configured.
- Corrections shall be conservative: a word is replaced only when the closest dictionary match has a Levenshtein edit distance of ≤ 2 and the word is at least 4 characters long.
- The following token classes shall be exempt from correction: ALL-CAPS tokens (abbreviations), tokens containing digits, tokens shorter than 4 characters, domain-specific vocabulary (business, strategy, digital-transformation, and technology terms).
- The corrected text shall be stored in a separate `auto_corrected_content` field on the block; the original OCR output in `content` must never be mutated.
- User-supplied manual corrections shall always override automatic corrections at export time.
- The spell corrector shall be toggleable via config (`spell_correction_enabled`).
- Diagram, table-cell, and URL blocks shall not be corrected.

### 3.6 Layout-to-Markdown Reconstruction

- The system shall reconstruct note content into Markdown with preserved logical order.
- The generated Markdown shall preserve, where possible:
  - title hierarchy using headings
  - bullets and numbered lists
  - code blocks
  - callouts
  - tables
  - emphasized text
  - inline labels
  - links between text and diagrams
- The system shall approximate handwritten spatial relationships using Markdown constructs and companion files.
- The system shall insert explicit placeholders or references when a paper construct cannot be faithfully represented in plain Markdown.
- The system shall produce stable file names and deterministic folder layout.

### 3.7 Tables

- The system shall detect tables and reconstruct them as Markdown tables when feasible.
- If a table cannot be represented reliably as Markdown, the system shall export a CSV, HTML, or image fallback and reference it from the Markdown note.
- The system shall preserve row and column order, headers, merged-cell semantics when detectable, and table captions or nearby labels.

### 3.8 Diagram Detection and Reconstruction

- The system shall detect diagrams separately from ordinary text blocks.
- The system shall classify diagrams into categories when possible, such as:
  - flowchart
  - sequence/process diagram
  - UML-like diagram
  - block diagram
  - architecture diagram
  - graph/network diagram
  - annotated sketch
  - chart/plot
- The system shall generate a source diagram file for each recognized diagram.
- Preferred outputs shall be:
  - PlantUML for diagrams representable as text-defined diagrams.
  - `.drawio` for free-form or geometrically positioned diagrams.
- The Markdown note shall reference each generated diagram source file.
- The system shall preserve diagram-local reading order, node labels, connectors, arrow directions, and grouping semantics when detectable.
- The system shall store original cropped diagram images for traceability.
- The system shall attach confidence and reconstruction notes for every generated diagram.
- The system shall support fallback behavior when reconstruction is uncertain:
  - attach the original cropped image
  - generate a placeholder section in Markdown
  - mark the diagram as requiring manual review

### 3.9 Charts and Graphs

- The system shall detect handwritten charts and graphs.
- When chart semantics are recoverable, the system shall reconstruct them into a structured representation and companion source file where practical.
- When semantics are not recoverable, the system shall preserve the chart as an extracted image and reference it from Markdown.

### 3.10 Visual Semantics

- The system shall attempt to preserve visual semantics including color usage, underlines, highlight markers, boxed regions, arrows, indentation, and grouping.
- The system shall convert visual semantics into Markdown-compatible notation or metadata where direct rendering is not possible.
- The system shall keep color metadata for future richer export formats.

### 3.11 Export and Storage

- The user shall be able to configure the destination folder for generated notes.
- The system shall export notes into a predictable directory structure, for example:
  - `course/session/notes.md`
  - `course/session/diagrams/*.drawio`
  - `course/session/diagrams/*.puml`
  - `course/session/assets/*`
- The system shall support repeated exports without uncontrolled duplication.
- The system shall support overwrite, versioned export, and merge modes.

### 3.12 Review Workflow

- The application shall present a review screen before final export.
- The review screen shall show:
  - original image
  - detected text blocks
  - detected structural regions
  - generated Markdown preview
  - generated diagram previews
  - confidence warnings
- The user shall be able to correct text and approve or reject diagram reconstructions.

### 3.13 Session Model

- The system shall support grouping pages into a note session.
- The session shall preserve page order and optionally support section grouping across multiple pages.
- The exported output shall support one Markdown file per page or one Markdown file per session.

## 4. Non-Functional Requirements

### 4.1 Accuracy

- The system shall optimize for high structural fidelity, not only raw OCR accuracy.
- The system shall target 80% to 90% perceived similarity between physical page and generated digital note.
- The system shall report measurable quality indicators, at minimum:
  - OCR confidence
  - layout confidence
  - table reconstruction confidence
  - diagram reconstruction confidence

### 4.2 Performance

- The system should process a single page in a time acceptable for desktop usage.
- The architecture shall support asynchronous batch processing.
- Long-running operations shall show progress, stage labels, and cancel support.

### 4.3 Cross-Platform

- The frontend shall run as a multiplatform Electron desktop application.
- The application shall support macOS, Windows, and Linux.
- The backend shall run locally using Python.

### 4.4 Privacy

- The preferred architecture shall be local-first.
- The system shall work without sending notebook content to external services by default.
- If optional remote AI services are later added, the user shall explicitly opt in.

### 4.5 Extensibility

- The architecture shall be modular so OCR, layout analysis, diagram recognition, and export modules can be swapped independently.
- The system shall support future addition of richer export targets such as Obsidian vault structures, HTML, PDF, and knowledge graph metadata.

### 4.6 Reliability

- The system shall never silently discard extracted content.
- When confidence is low, the system shall preserve the source crop and mark the issue for manual review.
- All pipeline stages shall emit logs and structured error details.

## 5. Architecture Requirements

### 5.1 Frontend

- The frontend shall use Electron.
- The UI shall support modern animated interactions using Motion and GSAP.
- The UI shall include at minimum:
  - import workspace
  - page ordering view
  - preprocessing preview
  - extraction progress view
  - Markdown preview
  - diagram preview
  - export configuration
  - review and correction workflow

### 5.2 Backend

- The backend shall be implemented in Python.
- The backend shall expose a clear service boundary to the Electron app, preferably via local HTTP API, IPC bridge, or background worker process.
- The backend shall separate the following stages:
  - ingestion
  - preprocessing
  - layout detection
  - OCR/HTR
  - structure assembly
  - diagram reconstruction
  - Markdown rendering
  - export

### 5.3 Data Model

- The system shall define canonical internal objects for:
  - page
  - block
  - line
  - token
  - table
  - diagram
  - asset
  - export artifact
  - session
- Every object shall carry source coordinates and confidence metadata.

## 6. Recommended Open-Source Technology Constraints

### 6.1 OCR and Document Parsing

The initial architecture shall evaluate and combine open-source libraries suited to document understanding and OCR:
- Docling for structured document conversion, OCR integration, table extraction, and Markdown export support.
- PaddleOCR for OCR and layout-related extraction tasks from images and PDFs.
- TrOCR for line-level handwritten text recognition where handwriting-specific recognition is required.

### 6.2 Computer Vision

- OpenCV shall be used for image preprocessing and geometric corrections.
- Additional CV models may be used for segmentation, contour detection, connector detection, and symbol localization.

### 6.3 Diagram Reconstruction

- PlantUML shall be used as a preferred textual target for diagrams that fit its notation.
- Draw.io / diagrams.net `.drawio` XML shall be used for free-form diagram output.
- The system may use conversion utilities between PlantUML and draw.io where useful, but native generation shall remain the target.

### 6.4 Storage and Metadata

- Markdown files shall remain plain text.
- Companion metadata should be stored as JSON or YAML.
- Diagram source files shall remain editable in their native source formats.

## 7. Quality and Validation Requirements

- The project shall define benchmark samples covering engineering notes, mixed text and diagrams, tables, multi-page sessions, and low-quality phone photos.
- The project shall include evaluation criteria for:
  - text recognition quality
  - structural ordering quality
  - diagram fidelity
  - table fidelity
  - export correctness
- The project shall include golden test fixtures with expected Markdown and diagram outputs.

## 8. Out of Scope for Initial Version

The first version does not need to guarantee:
- perfect recognition of arbitrary artistic sketches
- perfect recreation of highly irregular free-form layouts
- full semantic understanding of all engineering diagrams
- complete formula recognition for all mathematical notation
- real-time mobile capture inside the desktop app

## 9. Acceptance Criteria for Initial Release

The first usable release shall satisfy all of the following:
- Import a batch of notebook page images.
- Process them locally.
- Extract readable text in correct reading order for common note layouts.
- Reconstruct titles, paragraphs, bullets, and simple tables into Markdown.
- Detect diagrams and export either PlantUML, draw.io, or a manual-review fallback.
- Export notes and companion files into a user-defined folder structure.
- Provide a review UI showing original page, extracted structure, and output preview.
- Preserve enough page semantics that the resulting note is practically useful for study and archival.
