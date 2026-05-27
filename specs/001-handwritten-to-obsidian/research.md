# Research: Handwritten Notes to Obsidian Vault

**Phase**: 0 — Outline & Research
**Date**: 2026-05-27
**Plan**: [plan.md](./plan.md)

---

## Decision 1: Frontend Framework

**Decision**: Electron + React 18 + TypeScript

**Rationale**: Electron provides cross-platform desktop packaging (macOS, Windows,
Linux) with access to the local filesystem and a native IPC bridge to the Python
backend. React 18 with TypeScript gives a maintainable, type-safe component model.
No competing framework provides equivalent cross-platform coverage with comparable
ecosystem maturity for this use case.

**Alternatives considered**:
- Tauri: smaller binary, Rust-based — rejected because it would add Rust as a second
  backend language alongside Python, increasing complexity without proportional benefit.
- NW.js: older ecosystem, less active — rejected.
- Native (Swift/Qt): platform-specific or complex cross-platform build — rejected.

---

## Decision 2: State Management

**Decision**: Zustand

**Rationale**: The application's UI state (current session, page ordering, pipeline
stage progress, review corrections) is moderately complex but fits a flat store model.
Zustand's minimal API reduces boilerplate and is sufficient for the scope. Redux
Toolkit would be appropriate if the state graph becomes deeply nested or requires
complex middleware, but that is not anticipated for a single-user desktop app.

**Alternatives considered**:
- Redux Toolkit: more structure, more boilerplate — deferred; adopt if state complexity
  grows beyond Zustand's ergonomic range.
- Jotai / Valtio: smaller community, fewer integrations — rejected.

---

## Decision 3: Electron–Python IPC

**Decision**: Local HTTP via FastAPI + Uvicorn on a random available port, with the
port communicated to the Electron main process via stdout at startup.

**Rationale**: FastAPI over local HTTP is the cleanest boundary: the frontend calls
REST endpoints just like any web client; the API is independently testable with curl
or Postman; and the same API could be exposed to other clients in the future. Native
Electron IPC (contextBridge) is reserved for OS-level tasks (file-picker, tray icon,
window management) that cannot go through HTTP.

**Alternatives considered**:
- Electron child_process + stdin/stdout RPC: lower overhead but requires a custom
  protocol — rejected; non-standard and harder to test.
- gRPC: more efficient for high-throughput streaming — deferred; overkill for a
  single-user desktop app; adopt if pipeline streaming requires it.
- WebSockets (FastAPI): used for pipeline progress streaming (stage updates, confidence
  scores) alongside the REST API, not as a replacement.

---

## Decision 4: OCR Pipeline Composition

**Decision**: Docling (primary structured document backbone) + PaddleOCR (OCR
baseline and layout extraction) + Surya (reading order and non-linear layout) +
TrOCR (handwriting-specific line recognition fallback).

**Rationale**: No single library solves the full problem. Docling handles structured
document conversion and Markdown-oriented workflows. PaddleOCR provides the OCR
baseline and initial layout extraction. Surya handles reading-order determination on
non-linear page layouts (the hardest problem). TrOCR provides handwriting-specific
line recognition for lines that fail the general OCR path.

**Alternatives considered**:
- Tesseract: baseline quality; lacks reading-order support for non-linear layouts —
  available as adapter fallback but not primary.
- AWS Textract / Google Vision: cloud services — rejected, violates Principle I
  (Local-First & Privacy) as default.
- EasyOCR: good general OCR but weaker layout understanding — rejected as primary.

---

## Decision 5: Diagram Interpreter

**Decision**: Qwen2.5-VL 7B as primary local VLM. llama.cpp via `llama-cpp-python`
as the production inference runtime. Ollama as the developer-convenience runtime
for prototyping and evaluation.

**Rationale**: Qwen2.5-VL 7B is the strongest publicly available local model for
diagram and document understanding, supporting structured JSON output with bounding
boxes. llama.cpp provides direct GGUF execution, multimodal support, quantization
(Q4_K_M recommended for 6 GB footprint), and tighter performance control for
production deployment. Ollama wraps llama.cpp with a simpler API and is ideal during
development. The VLM MUST output constrained JSON (nodes, edges, labels, type,
confidence); Python validators normalize it; deterministic renderers generate
PlantUML / Mermaid / draw.io XML.

**Alternatives considered**:
- Qwen2.5-VL 3B: lower VRAM (≈3.2 GB) — available as fallback for constrained
  hardware; lower reconstruction quality.
- Qwen2.5-VL 32B: higher quality — deferred; requires significant GPU RAM.
- GPT-4V / Claude Vision: cloud — rejected, violates Principle I.
- SmolDocling / SmolVLM: too small for high-fidelity diagram interpretation —
  designated as preview/fallback model only.

---

## Decision 6: Diagram Output Format

**Decision**: PlantUML (`.puml`) for structured text-definable diagrams (flowcharts,
sequence, UML, block, architecture). draw.io XML (`.drawio`) for free-form geometry-
heavy diagrams (annotated sketches, spatial graphs). Mermaid as a secondary option
for simple flow/state/sequence diagrams when PlantUML is overkill.

**Rationale**: PlantUML is text-based, version-control friendly, and renders in
Obsidian via the PlantUML plugin. draw.io covers free-form layouts where explicit
geometry is needed. Both are open-source with well-documented XML/text schemas.

**Alternatives considered**:
- SVG output: vector but not editable as a diagram source — rejected.
- Mermaid only: weaker for complex UML/architecture diagrams — kept as secondary.

---

## Decision 7: Background Processing

**Decision**: Python `asyncio` + FastAPI background tasks for initial implementation.
Celery with Redis broker as an upgrade path if batch workloads require it.

**Rationale**: For a single-user desktop app, asyncio-native background tasks inside
FastAPI are sufficient and require no additional infrastructure. Celery is available
as an upgrade if sessions with 50+ pages create contention, but introducing a Redis
dependency on day one is premature.

**Alternatives considered**:
- RQ (Redis Queue): simpler than Celery — available as an alternative to Celery if
  upgrade is needed, but asyncio deferred first.
- ThreadPoolExecutor: fine for CPU-bound preprocessing but lacks progress streaming —
  used internally within asyncio workers for OpenCV operations.

---

## Decision 8: Testing Strategy

**Decision**: pytest + pytest-asyncio for all Python backend tests. Vitest for
TypeScript/Electron renderer unit tests. Golden fixture regression as the primary
quality gate for all pipeline stages (Principle V).

**Golden fixture structure**:
```
tests/golden/
  layout/
    engineering-notes-single-page/
      input.jpg
      expected-blocks.json
  tables/
    simple-3x3/
      input.jpg
      expected-markdown.md
  diagrams/
    flowchart-basic/
      input.jpg
      expected-plantuml.puml
    sequence-diagram/
      input.jpg
      expected-plantuml.puml
  ocr/
    mixed-heading-list/
      input.jpg
      expected-text.md
```

**Rationale**: Structural reconstruction quality is too subjective for unit tests
alone. Golden fixtures make quality measurable, catch regressions on OCR/layout
changes, and provide a benchmark corpus for evaluating new model versions.

---

## Decision 9: Obsidian Vault Integration

**Decision**: Direct filesystem write to the configured vault root. YAML front
matter generated by `python-frontmatter`. Obsidian-specific notation: `==highlight==`
for highlights, `> [!NOTE]` callout blocks, `![[file]]` embed links for diagrams.

**Rationale**: Obsidian has no API for external writes — it reads from the filesystem.
Writing directly to the vault is the canonical integration method. The front matter
format follows Obsidian's native YAML conventions. Obsidian-specific Markdown
extensions (`==`, `![[]]`, callout syntax) are used for visual semantics because
they render correctly in Obsidian and degrade gracefully in standard Markdown renderers.

**Alternatives considered**:
- Obsidian Local REST API plugin: requires user to install a third-party plugin —
  rejected as a dependency; filesystem write is simpler and more reliable.
- Standard CommonMark only: loses Obsidian-specific features (highlights, embeds,
  callouts) — rejected; the spec explicitly requires Obsidian-compatible notation.

---

## Decision 10: Resolved Clarifications

All items from the spec were resolved without needing user input:

| Topic | Resolution |
|-------|-----------|
| Electron IPC mechanism | Local HTTP (FastAPI) for pipeline; native IPC for OS tasks |
| State management library | Zustand (Redux Toolkit if complexity grows) |
| VLM inference runtime | llama.cpp (production), Ollama (dev/prototyping) |
| Background processing | asyncio + FastAPI background tasks; Celery as upgrade path |
| Obsidian write mechanism | Direct filesystem; python-frontmatter for front matter |
| Table fallback format | CSV preferred; HTML or image crop if CSV not recoverable |
| Session export mode default | Overwrite mode default; versioned and merge as user options |
