# hand2notes

hand2notes is a local-first desktop application that converts mobile phone photos of handwritten notebook pages into Markdown notes plus companion diagram files.

The target is not only OCR. The target is structural reconstruction: reading order, headings, tables, callouts, colors, diagram intent, and session organization, with an expected practical similarity of roughly 80% to 90% versus the physical notebook page.[web:1][web:3][web:17]

## Goal

The project is designed for handwritten engineering and study notes where a page may contain mixed content such as:
- headings and paragraphs
- bullets and numbered lists
- tables
- arrows and callouts
- free-form sketches
- architecture or process diagrams
- highlighted or color-coded areas

The output should be a clean Markdown note plus editable diagram source files, stored in a user-defined folder structure.

## Core Product Idea

Input:
- One image, many images, or a full ordered session of notebook page photos taken with a mobile phone.

Output:
- Markdown files.
- `.puml` files for diagrams representable in PlantUML.
- `.drawio` files for free-form diagrams that require explicit geometry.
- Companion assets and metadata files.

## Proposed Architecture

### Frontend

- Electron desktop app.
- Motion for declarative UI motion and transitions.
- GSAP for timeline-driven animations, advanced transitions, and diagram/page-stage visualizations.
- React + TypeScript is the recommended frontend stack inside Electron for maintainability.
- Zustand or Redux Toolkit for app state, depending on complexity.

### Backend

- Python backend running locally.
- FastAPI recommended for a local API boundary between Electron and Python.
- Background workers for OCR, preprocessing, and export stages.
- Pydantic models for canonical page/block/diagram/session schemas.

### Pipeline

1. Import and order notebook images.
2. Preprocess images: crop, deskew, dewarp, denoise, normalize.
3. Detect layout regions and reading order.
4. Run OCR / handwritten text recognition.
5. Detect tables, diagrams, labels, arrows, and callouts.
6. Reconstruct note structure.
7. Generate Markdown and diagram source files.
8. Review in UI.
9. Export into a notes folder.

## Recommended Open-Source Libraries

### Document parsing and OCR

| Library | Role in hand2notes | Why it matters |
|---|---|---|
| Docling | Document conversion, OCR integration, structured extraction, Markdown-oriented output | Docling supports OCR-backed document conversion, images as inputs, multiple OCR engines, and Markdown export workflows.[web:1][web:2][web:3][web:14] |
| PaddleOCR | General OCR, layout-related extraction, line/region detection | PaddleOCR is an open-source OCR toolkit for images and PDFs and is a strong baseline for page text extraction.[web:23] |
| TrOCR | Handwriting recognition for cropped text lines | Microsoft TrOCR handwritten models are intended for single text-line OCR, useful after page segmentation.[web:44][web:48] |
| Surya | Layout analysis, reading order, table recognition, OCR | Surya is described as supporting OCR, layout analysis, reading order, and table recognition, which matches the structure-first goal.[web:49][web:52][web:58] |

### Computer vision and preprocessing

| Library | Role in hand2notes |
|---|---|
| OpenCV | Deskewing, contour detection, page boundary detection, perspective correction, denoising, morphology, connector detection |
| scikit-image | Additional image cleanup, thresholding, morphology, segmentation utilities |
| NumPy | Core image and geometry operations |
| Pillow | Basic raster loading, conversion, annotation, and image export |

### Diagram generation and conversion

| Library / Tool | Role in hand2notes | Notes |
|---|---|---|
| PlantUML | Text-defined output for UML-like, flow, process, and architecture diagrams | Good target for structured diagrams; can be enriched with styling and annotations.[web:15] |
| draw.io / diagrams.net | Output target for free-form diagrams | The desktop app is Electron-based and open source under Apache 2.0.[web:50][web:53] |
| plantuml_to_drawio | Optional conversion utility | Demonstrates conversion from PlantUML into draw.io XML, useful for interoperability.[web:21] |

### Markdown and note storage

| Library | Role in hand2notes |
|---|---|
| python-frontmatter or PyYAML | Metadata frontmatter generation |
| Jinja2 | Templated Markdown rendering |
| markdown-it / unified ecosystem | Preview rendering in the frontend |

### Application and job infrastructure

| Library | Role in hand2notes |
|---|---|
| FastAPI | Local API between Electron and Python |
| Uvicorn | Local ASGI server |
| Pydantic | Typed schemas for pages, blocks, diagrams, sessions |
| SQLModel or SQLite | Local job state, runs, artifacts, and review status |
| Celery or RQ | Optional background processing if the local pipeline becomes heavy |

## Technology Recommendations

### Strong recommendations

- Electron + React + TypeScript for the desktop UI.
- Motion for state transitions and interface micro-interactions.
- GSAP for richer timeline orchestration, onboarding, progress choreography, and diagram-stage visualization.
- Python + FastAPI for the local backend.
- OpenCV as mandatory preprocessing infrastructure.
- Docling as the first structured-document backbone to evaluate.[web:1][web:3][web:17]
- PaddleOCR as the first OCR baseline.[web:23]
- TrOCR as a specialized fallback for handwritten lines, not as the only full-page recognizer.[web:44][web:45]
- Surya as a high-value candidate for reading order and region understanding.[web:49][web:52][web:58]

### Storage recommendations

Recommended export tree:

```text
exports/
  notebook-name/
    session-YYYY-MM-DD-topic/
      notes.md
      metadata.json
      diagrams/
        001-system-overview.puml
        002-cache-flow.drawio
      assets/
        page-001-original.jpg
        page-001-diagram-01.png
        page-001-table-01.csv
```

### UX recommendations

The application should expose explicit pipeline stages instead of one opaque “Process” button:
- Import
- Clean image
- Detect structure
- Recognize text
- Rebuild note
- Review diagrams
- Export

This matters because diagram reconstruction and reading-order errors need user visibility.

## Hard Problems

These are the hard parts of the project, in order:

1. Reading order on non-linear handwritten pages.
2. Handwritten diagram understanding.
3. Distinguishing text blocks from diagram labels and connector annotations.
4. Table reconstruction from irregular hand-drawn grids.
5. Preserving layout intent in Markdown, which is structurally limited.
6. Achieving stable 80% to 90% similarity without producing noisy output.

## Recommended Internal Modules

```text
hand2notes/
  apps/
    electron-ui/
    python-api/
  packages/
    core_models/
    ingestion/
    preprocessing/
    layout/
    ocr/
    tables/
    diagrams/
    markdown_export/
    review/
    storage/
  samples/
  tests/
  docs/
```

Suggested Python backend modules:
- `preprocessing`: OpenCV and image normalization.
- `layout`: region segmentation, reading order, page graph.
- `ocr`: adapters for PaddleOCR, TrOCR, and Docling-backed OCR.
- `tables`: table cell extraction and Markdown/CSV rendering.
- `diagrams`: classification, node/edge extraction, PlantUML/draw.io generation.
- `markdown_export`: final note rendering.
- `review`: issue flags, confidence thresholds, manual corrections.

## Delivery Strategy

Recommended build order:

### Phase 1
- Batch image import.
- Preprocessing.
- OCR baseline.
- Basic Markdown export.
- Session folder export.

### Phase 2
- Layout reconstruction.
- Title/list/table detection.
- Review UI.
- Confidence overlays.

### Phase 3
- Diagram detection.
- PlantUML generation for structured diagrams.
- `.drawio` generation for free-form diagrams.
- Manual review workflow for diagram corrections.

### Phase 4
- Color semantics.
- Formula handling.
- Obsidian-oriented export refinements.
- Quality benchmarks and regression fixtures.

## Notes on Feasibility

A single library will not solve this project. The realistic approach is a staged pipeline that combines preprocessing, region detection, OCR/HTR, structural reconstruction, and specialized diagram generation.[web:1][web:23][web:44][web:52]

Docling is strong for structured document conversion and Markdown-oriented workflows, but handwritten notebooks with free-form diagrams will still require custom CV and post-processing layers.[web:1][web:3][web:17]

TrOCR is useful for handwritten text lines, but not sufficient alone for full-page notebook parsing without segmentation.[web:44][web:45]

Surya and PaddleOCR are relevant because the core problem is not only text recognition but also layout, tables, and reading order.[web:23][web:49][web:52][web:58]

## License Direction

Prefer a permissive project license unless there is a reason to enforce copyleft:
- Apache-2.0
- MIT

This matches well with the recommended ecosystem, including diagrams.net desktop being available under Apache 2.0.[web:50][web:53]

## References Used for Initial Technology Direction

- Docling documentation and quickstart.[web:1][web:2][web:3]
- Docling supported formats and OCR options.[web:14][web:18]
- PaddleOCR repository.[web:23]
- TrOCR handwritten model documentation.[web:44][web:48]
- Surya descriptions for OCR, layout analysis, reading order, and table recognition.[web:49][web:52][web:58]
- PlantUML annotation guide.[web:15]
- draw.io desktop repository and licensing notes.[web:50][web:53]
- PlantUML to draw.io conversion utility.[web:21]
