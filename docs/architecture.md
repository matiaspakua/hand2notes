# Architecture Overview

hand2notes converts mobile phone photos of handwritten notebook pages into structured Markdown notes exported to an Obsidian vault. The system runs entirely locally.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Desktop App                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Import Page │  │ Review Page  │  │  Settings/Export │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                │                   │              │
│         └────────────────┼───────────────────┘              │
│                          │  HTTP / WebSocket                │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Python FastAPI Backend                     │
│  ┌────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │  Sessions  │  │   Pipeline    │  │      Config        │  │
│  │  Router    │  │   Orchestrator│  │      Router        │  │
│  └────────────┘  └───────┬───────┘  └────────────────────┘  │
│                          │                                   │
│         ┌────────────────▼────────────────┐                 │
│         │           9 Pipeline Stages     │                 │
│         │  1. Import (HEIC/JPG/PNG)        │                 │
│         │  2. Preprocess (deskew/denoise)  │                 │
│         │  3. Detect Layout (Surya)        │                 │
│         │  4. Recognize Text (OCR)         │                 │
│         │     + Visual Semantics sub-step  │                 │
│         │  5. Reconstruct Structure        │                 │
│         │     + Table extraction sub-step  │                 │
│         │  6. Detect Diagrams (VLM)        │                 │
│         │  7. Generate Output              │                 │
│         └────────────────┬────────────────┘                 │
│                          │                                   │
│    ┌─────────────────────┼─────────────────────────┐        │
│    │                     │                         │        │
│    ▼                     ▼                         ▼        │
│  SQLite DB         Markdown Export           Obsidian Vault  │
│  (SQLModel)        (vault_writer)            (local files)   │
└─────────────────────────────────────────────────────────────┘
```

## Monorepo Structure

See [monorepo-structure.md](./monorepo-structure.md) for the full package breakdown.

## Getting Started

See [specs/001-handwritten-to-obsidian/quickstart.md](../specs/001-handwritten-to-obsidian/quickstart.md) for development setup.

## Key Design Principles

1. **Local-First**: No network calls in default pipeline. All ML runs locally via llama.cpp or Ollama.
2. **Observable Pipeline**: 9 named stages, each with typed input/output and progress events.
3. **Fidelity Over Silence**: Every low-confidence block preserves source crop + review flag.
4. **Modular & Swappable**: OCR/layout/VLM adapters in isolated packages.
5. **Test-First with Fixtures**: Golden fixtures for all pipeline stages.
