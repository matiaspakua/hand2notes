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


## Local Diagram Understanding Model

The diagram reconstruction stage should include a local multimodal model that acts as the primary diagram interpreter before generating `.drawio`, PlantUML, or Mermaid outputs.

### Role in the pipeline

Proposed diagram pipeline:

1. Detect diagram regions using layout/CV models.
2. Crop each diagram and collect nearby labels and OCR text.
3. Send the crop plus OCR/context to a local vision-language model.
4. Ask the model to produce a structured intermediate JSON representation, for example:
   - nodes
   - edges
   - labels
   - arrow directions
   - containers/groups
   - diagram type
   - confidence
5. Convert that JSON into one of:
   - PlantUML for structured diagrams
   - Mermaid for simple flow/state/sequence diagrams
   - `.drawio` XML for free-form geometry-heavy diagrams
6. Store the original crop and confidence report for manual review.

### Candidate open-source local models

| Model | Why it is relevant | Pros | Cons | Fit for hand2notes |
|---|---|---|---|---|
| Qwen2.5-VL | Strong document and diagram understanding, local deployment through Ollama/Hugging Face | Good visual reasoning; can analyze charts, graphics, layouts, and output structured JSON with coordinates; available in 3B, 7B, 32B, 72B variants | Larger variants require significant GPU/RAM; still needs prompt design and post-validation | **Best primary candidate** [web:126][web:129][web:135] |
| Granite-Vision / Granite-Docling | Integrates well with Docling VLM pipeline and local document workflows | Good local integration inside Docling; useful for page/document tasks | Less directly positioned as the strongest diagram interpreter | Good secondary option inside Docling-centered pipeline [web:111][web:112] |
| SmolDocling / SmolVLM | Very small local models for cheap inference and fallback tasks | Lightweight; practical for CPU/M-series fallback | Too small to be the main high-fidelity diagram interpreter | Good fallback / preview model, not main interpreter [web:111][web:112] |
| DeepSeek-OCR-3B | VLM-oriented OCR/document conversion option in Docling catalog | Good for Markdown conversion workflows | More document conversion focused than diagram-graph reconstruction | Secondary experimental option [web:112] |
| Phi-4-Multimodal / Pixtral / Gemma vision options | Available in Docling catalog for local multimodal use | Strong general multimodal capability | More integration and evaluation work; weaker evidence here for diagram-first choice | Benchmark candidates, not first pick [web:112] |

### Selection

Best-guess choice for the main local diagram interpreter: **Qwen2.5-VL**.

Reason:
- It is explicitly described as strong at understanding documents and diagrams.
- It can analyze charts, icons, graphics, and layouts.
- It can generate structured outputs and stable JSON.
- It can localize objects with bounding boxes or points, which is useful for node-edge reconstruction.
- It is available locally through Ollama in several sizes, making phased deployment practical. [web:126][web:129][web:135]

### Recommended deployment choice

- Default high-quality model: `qwen2.5vl:7b`
- Low-resource fallback: `qwen2.5vl:3b`
- Future high-end option: `qwen2.5vl:32b`

The 7B model is the best practical balance for local quality versus hardware requirements, while the 3B model is suitable for laptops with tighter memory constraints. Ollama lists the 3B model at about 3.2GB and the 7B model at about 6.0GB. [web:126]

### Why not use the VLM alone

The VLM should not directly emit final `.drawio` or PlantUML without an intermediate schema.

Safer architecture:
- VLM produces constrained JSON.
- Python validators normalize the JSON.
- Deterministic renderers generate PlantUML, Mermaid, or `.drawio`.
- Review UI shows diff between source crop and reconstructed diagram.

This reduces hallucination risk and keeps diagram generation testable.

## Updated Recommended Stack

### Core backend

- Python 3.12+
- FastAPI
- Pydantic
- OpenCV
- NumPy
- scikit-image
- Pillow

### OCR and layout

- Docling as structured document backbone. [web:1][web:112]
- PaddleOCR for OCR baseline and table/layout extraction. [web:23]
- Surya for reading order and non-linear layout understanding. [web:58]
- TrOCR for handwriting line recognition fallback. [web:44][web:47]

### Diagram understanding

- Qwen2.5-VL as the primary local diagram interpreter. [web:126][web:129]
- `llama.cpp` as the recommended production inference runtime for the diagram-interpreter VLM because it provides direct GGUF execution, multimodal support, quantization control, and lower-level performance tuning for local inference. [web:150][web:164]
- Ollama as the fast prototyping and developer-convenience runtime for the same model family. [web:126]
- Optional Docling VLM integration for figure classification and local picture description. [web:111][web:112]
- Custom Python schema to represent nodes, edges, containers, and styling.

### Diagram generation

- PlantUML for structured engineering diagrams. [web:15]
- Mermaid for simple flow/state/sequence diagrams.
- Draw.io / diagrams.net XML for free-form diagram reconstruction. [web:50][web:53]

### Frontend

- Electron
- React
- TypeScript
- Motion
- GSAP
- Markdown preview based on markdown-it or unified ecosystem

### Local model runtime

- `llama.cpp` as the recommended default production runtime for the vision-language diagram model. It supports multimodal inference and Qwen2.5-VL GGUF deployment, and is the preferred path when optimizing for lower overhead and tighter performance control. [web:150][web:164]
- Ollama as the recommended prototyping and developer-experience runtime, useful for fast evaluation and simpler local setup. [web:126]
- Hugging Face Transformers as an advanced path for direct Python inference and tighter pipeline control. [web:112]

### Recommended decision

If only one local multimodal model is selected now, use **Qwen2.5-VL 7B with `llama.cpp` as the primary production runtime** for the diagram interpreter in the pipeline, with deterministic Python renderers for PlantUML, Mermaid, and `.drawio` generation. Use Ollama only as the convenience path for prototyping and evaluation. [web:126][web:129][web:135][web:150][web:164]

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
