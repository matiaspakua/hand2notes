<!-- SYNC IMPACT REPORT
Version change: (none) → 1.0.0
Modified principles: (initial ratification — no prior principles)
Added sections:
  - Core Principles (5 principles): Local-First & Privacy, Staged Observable Pipeline,
    Fidelity Over Silence, Modular & Swappable Components, Test-First with Golden Fixtures
  - Technology Stack Constraints
  - Development Workflow
  - Governance
Removed sections: none (first version)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ reviewed — Constitution Check gate placeholder
    is intentionally generic; no update required
  - .specify/templates/spec-template.md ✅ reviewed — no changes required
  - .specify/templates/tasks-template.md ✅ reviewed — no changes required
Follow-up TODOs: none — all placeholders resolved
-->

# hand2notes Constitution

## Core Principles

### I. Local-First & Privacy (NON-NEGOTIABLE)

The system MUST process all notebook content locally by default. No image, extracted
text, or user data may be transmitted to external services unless the user explicitly
opts in through a clearly labeled, opt-in-only setting. Local Ollama models are the
required default runtime for all AI inference; remote API calls are opt-in only.

**Rationale**: Engineering and study notebooks contain sensitive academic and professional
content. Privacy-by-default is a hard constraint, not a configurable preference.

### II. Staged, Observable Pipeline

The processing pipeline MUST be decomposed into discrete, named stages:
Import → Preprocess → Detect Layout → Recognize Text → Reconstruct Structure →
Detect Diagrams → Generate Output → Review → Export.

Each stage MUST:
- Accept a well-defined Pydantic input schema.
- Produce a well-defined Pydantic output schema.
- Emit structured logs and per-block confidence scores.
- Be testable in isolation without running the full pipeline.

A single opaque "Process" button that conceals all stages is prohibited. Progress
indicators, stage labels, and cancel support are mandatory for every long-running
operation.

**Rationale**: Diagram reconstruction and reading-order errors require user visibility;
an opaque pipeline makes debugging and quality improvement impossible.

### III. Fidelity Over Silence (NON-NEGOTIABLE)

The system MUST target 80%–90% structural fidelity to the original notebook page.
The system MUST NEVER silently discard extracted content.

When confidence is below acceptable thresholds:
- The source crop MUST be preserved.
- The low-confidence block MUST be explicitly marked in the output.
- A manual-review flag MUST be attached.

Uncertain output flagged for review is acceptable. Silent omission is not.

**Rationale**: A note that misleads through missing content is worse than one that
prompts the user to verify a difficult section.

### IV. Modular & Independently Swappable Components

OCR engines, layout analyzers, diagram interpreters, and export renderers MUST be
implemented behind clearly defined adapter interfaces. No pipeline stage may carry
a hard dependency on a specific library at the call-site level.

Preferred defaults: Docling + PaddleOCR + Surya for OCR/layout; Qwen2.5-VL via
Ollama for diagram interpretation; PlantUML and draw.io XML for diagram output.

Any module swap MUST require only a configuration or adapter change, not a rewrite
of the stages that call it.

**Rationale**: The OCR/AI ecosystem evolves rapidly. Architectural modularity protects
against library deprecation and enables incremental quality improvements without
disrupting the full pipeline.

### V. Test-First with Golden Fixtures

New pipeline capabilities MUST be preceded by test fixtures that define expected
output before implementation begins. Every diagram type, table variant, and note
layout category MUST have at minimum one golden fixture.

Benchmark samples MUST cover: engineering notes, mixed text+diagrams, tables,
multi-page sessions, and low-quality phone photos.

Regression against golden fixtures MUST be the primary quality gate for any change
to OCR, layout, or diagram stages.

**Rationale**: Structural reconstruction is subjective enough that "looks right" is
insufficient as a quality standard; fixtures make quality measurable and regressions
detectable.

## Technology Stack Constraints

The following technology choices are non-negotiable for the initial architecture.
Changes require a constitution amendment.

**Frontend**: Electron + React + TypeScript. Motion for declarative UI state
transitions. GSAP for timeline-driven animations and diagram-stage visualization.

**Backend**: Python 3.12+. FastAPI for the local API boundary between Electron and
Python. Pydantic for all canonical data models (page, block, line, token, table,
diagram, asset, session). Every object MUST carry source coordinates and confidence
metadata.

**OCR / Layout**: Docling (structured document backbone), PaddleOCR (OCR baseline
and layout), Surya (reading order and non-linear layout understanding), TrOCR
(handwritten line recognition fallback).

**Diagram Interpretation**: Qwen2.5-VL 7B via Ollama as the primary local
vision-language model. VLM output MUST be constrained JSON validated by Python
schemas; deterministic Python renderers MUST generate the final PlantUML / Mermaid /
draw.io artifacts. The VLM MUST NOT emit final diagram files directly.

**Diagram Output**: PlantUML for structured text-defined diagrams. draw.io XML for
free-form geometry-heavy diagrams.

**Storage**: Plain-text Markdown for notes. JSON or YAML for companion metadata.
SQLite via SQLModel for local job state, pipeline runs, artifacts, and review status.

**License**: Apache-2.0 or MIT. No GPL-licensed runtime dependencies may be introduced
without an explicit constitutional amendment and migration plan.

## Development Workflow

- Implementation MUST follow the phased delivery order from `README.md`:
  Phase 1 (import, preprocess, OCR, basic export) → Phase 2 (layout, review UI) →
  Phase 3 (diagrams) → Phase 4 (color semantics, formulas, benchmarks).
- Features MUST NOT skip phases or bundle multiple phase concerns into one increment.
- All pipeline stage input/output schemas MUST be reviewed and approved before
  implementation of that stage begins.
- Every PR touching OCR, layout, or diagram stages MUST include a fixture test or
  explicit written justification for why one is not feasible.
- Complexity MUST be justified in the `plan.md` Complexity Tracking table before
  being introduced into the codebase.

## Governance

This constitution supersedes all other project practices. Any conflict between a
guideline, PR convention, or tooling default and this document is resolved in favor
of this document.

**Amendment procedure**:
1. Propose the change with explicit rationale and version bump type (MAJOR/MINOR/PATCH).
2. Update `.specify/memory/constitution.md` with the revised content.
3. Propagate changes to dependent templates and run `/speckit-constitution`.
4. Record the amendment in the Sync Impact Report comment at the top of this file.

**Versioning policy**:
- MAJOR: Removal or incompatible redefinition of an existing principle.
- MINOR: New principle, section added, or materially expanded guidance.
- PATCH: Clarification, wording improvement, or typo fix.

**Compliance review**: All plans MUST include a Constitution Check gate (see
`plan-template.md`). The gate MUST pass before Phase 0 research begins and MUST
be re-checked after Phase 1 design completes.

**Version**: 1.0.0 | **Ratified**: 2026-05-27 | **Last Amended**: 2026-05-27
