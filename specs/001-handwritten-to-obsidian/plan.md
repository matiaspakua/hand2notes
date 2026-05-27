# Implementation Plan: Handwritten Notes to Obsidian Vault

**Branch**: `002-impl-plan-core-pipeline` | **Date**: 2026-05-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-handwritten-to-obsidian/spec.md`

## Summary

Convert mobile phone photos of handwritten notebook pages into structured Markdown
notes and companion diagram files, then export them into an Obsidian vault with
correct folder structure and YAML front matter. The pipeline runs entirely locally
across 9 named stages (Import → Preprocess → Detect Layout → Recognize Text →
Reconstruct Structure → Detect Diagrams → Generate Output → Review → Export),
driven by a Python FastAPI backend and surfaced in an Electron desktop UI.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.x (Electron frontend)

**Primary Dependencies**:
- Backend: FastAPI, Uvicorn, Pydantic v2, OpenCV, NumPy, scikit-image, Pillow,
  Docling, PaddleOCR, Surya, TrOCR (Hugging Face), SQLModel, python-frontmatter,
  Jinja2, llama-cpp-python (production VLM), Ollama client (prototyping VLM)
- Frontend: Electron, React 18, TypeScript, Motion, GSAP, markdown-it, Zustand

**Storage**: SQLite via SQLModel (pipeline job state, runs, review status);
plain-text Markdown + YAML front matter (exported notes); JSON (session metadata);
PlantUML `.puml` + draw.io `.drawio` XML (diagram source files)

**Testing**: pytest + pytest-asyncio (Python backend); Vitest (TypeScript/Electron
renderer); golden fixture regression tests for all pipeline stages

**Target Platform**: Electron desktop app — macOS, Windows, Linux

**Project Type**: desktop-app (Electron frontend + local Python FastAPI backend)

**Performance Goals**: Single notebook page processed end-to-end in ≤ 2 minutes
on a modern laptop (M-series Mac or equivalent x86); batch sessions support
async processing with per-stage progress reporting

**Constraints**: fully offline-capable; no network calls in default pipeline;
local VLM via llama.cpp (Qwen2.5-VL 7B ≈ 6 GB VRAM/RAM); all content stays
on device unless user explicitly enables remote AI opt-in

**Scale/Scope**: single-user desktop application; sessions of 1–100+ pages;
Obsidian vault may contain thousands of existing notes — exports must not corrupt them

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Local-First & Privacy | No network calls in default pipeline; VLM runs via llama.cpp locally; Obsidian vault writes are local filesystem only | ✅ PASS |
| II. Staged, Observable Pipeline | 9 named stages; each stage has a typed Pydantic input/output schema; progress + cancel exposed in UI; opaque single-button processing prohibited | ✅ PASS |
| III. Fidelity Over Silence | Every low-confidence block preserves source crop + review flag; no silent content discard anywhere in pipeline | ✅ PASS |
| IV. Modular & Swappable | OCR/layout/diagram adapters in isolated packages; no direct library imports at call-site level; swap = config/adapter change only | ✅ PASS |
| V. Test-First with Fixtures | Golden fixtures required before implementing each diagram type, table variant, layout category; fixture regression is primary quality gate | ✅ PASS — fixtures must be created before each stage implementation |

**Post-Phase 1 re-check**: required after data-model.md and contracts/ are complete.

## Project Structure

### Documentation (this feature)

```text
specs/001-handwritten-to-obsidian/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── pipeline-api.md
│   ├── session-api.md
│   └── config-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
hand2notes/
├── apps/
│   ├── electron-ui/              # Electron + React + TypeScript frontend
│   │   ├── src/
│   │   │   ├── main/             # Electron main process
│   │   │   ├── renderer/         # React UI
│   │   │   │   ├── components/   # Shared UI components
│   │   │   │   ├── pages/        # Import, Review, Export, Settings screens
│   │   │   │   ├── stores/       # Zustand state slices
│   │   │   │   └── services/     # HTTP client to Python backend
│   │   │   └── preload/          # Electron preload scripts
│   │   ├── tests/
│   │   └── package.json
│   └── python-api/               # Python FastAPI backend
│       ├── src/
│       │   └── hand2notes/
│       │       ├── api/          # FastAPI routers (sessions, pipeline, config)
│       │       ├── pipeline/     # Stage orchestration
│       │       └── adapters/     # OCR, layout, diagram, export adapters
│       ├── tests/
│       │   ├── fixtures/         # Golden fixture images + expected outputs
│       │   ├── unit/
│       │   └── integration/
│       └── pyproject.toml
├── packages/
│   ├── core_models/              # Pydantic schemas: Page, Block, Diagram, Session…
│   ├── ingestion/                # Image import, ordering, format validation
│   ├── preprocessing/            # OpenCV: deskew, dewarp, denoise, normalize
│   ├── layout/                   # Region detection, reading order (Surya)
│   ├── ocr/                      # Adapters: Docling, PaddleOCR, TrOCR
│   ├── tables/                   # Table cell extraction, Markdown/CSV rendering
│   ├── diagrams/                 # Diagram classify, VLM interpret, PlantUML/drawio gen
│   ├── markdown_export/          # Note rendering, Obsidian front matter, Jinja2
│   ├── review/                   # Confidence flags, corrections, review state
│   └── storage/                  # SQLite job state, artifact registry
├── samples/                      # Sample notebook page images for development
├── tests/                        # Cross-package integration tests
│   └── golden/                   # Golden fixtures per content type
└── docs/
```

**Structure Decision**: Monorepo with two apps (electron-ui + python-api) and 10
isolated Python packages. Justified by Principle IV (Modular & Swappable): each
pipeline stage lives in its own package with defined adapter interfaces, enabling
independent replacement of OCR engines, layout analyzers, and diagram interpreters
without touching calling code.

## Complexity Tracking

| Entry | Why Needed | Simpler Alternative Rejected Because |
|-------|------------|--------------------------------------|
| Two app containers (Electron + Python API) | Electron cannot run Python ML libraries natively; Python cannot build a cross-platform desktop UI | Single-language approach requires either abandoning Python's CV/ML ecosystem or abandoning Electron's cross-platform desktop capabilities |
| 10 Python packages (monorepo) | Principle IV mandates each pipeline stage be independently swappable; a single package would create tight coupling between OCR engines, layout models, and diagram generators | Flat single-package structure would make adapter isolation impractical and violate Principle IV |
