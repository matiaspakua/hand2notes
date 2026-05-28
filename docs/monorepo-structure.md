# Monorepo Structure

```
hand2notes/
├── apps/
│   ├── electron-ui/              # Electron + React + TypeScript desktop UI
│   │   └── src/
│   │       ├── main/             # Electron main process + tray + file picker
│   │       ├── preload/          # contextBridge for renderer → main IPC
│   │       └── renderer/
│   │           ├── components/   # ConfidenceBadge, BlockEditor, DiagramPreview,
│   │           │                 #   DiagramReviewControls, MarkdownPreview,
│   │           │                 #   TablePreview
│   │           ├── pages/        # ImportPage, ProcessingPage, ReviewPage,
│   │           │                 #   ExportPage, SettingsPage
│   │           ├── stores/       # sessionStore, pipelineStore, reviewStore
│   │           └── services/     # api.ts (typed HTTP client)
│   │
│   └── python-api/               # FastAPI backend
│       └── src/hand2notes/
│           ├── api/
│           │   ├── routers/      # sessions.py, pipeline.py, config.py
│           │   ├── middleware.py # RFC 7807 error responses, request logging
│           │   ├── main.py       # app factory, static mounts, router registration
│           │   └── config_service.py  # VaultConfig load/save/validate
│           └── pipeline/
│               └── orchestrator.py   # 9-stage async pipeline runner
│
├── packages/
│   ├── core_models/    # Pydantic v2 schemas: Session, Page, Block, DiagramBlock,
│   │                   #   TableBlock, VaultConfig, BoundingBox, VisualSemantics
│   ├── ingestion/      # Image import + HEIC→JPEG conversion
│   ├── preprocessing/  # Deskew, denoise, highlight_detector, shape_detector
│   ├── layout/         # Surya layout detection, reading order, semantics_mapper
│   ├── ocr/            # PaddleOCR + TrOCR adapters, Docling, OCR orchestrator,
│   │                   #   URL detector
│   ├── tables/         # Table detector, cell extractor, Markdown/CSV/image renderers
│   ├── diagrams/       # VLM clients (Ollama, llama.cpp), validator, PlantUML/draw.io renderers
│   │                   #   crop saver
│   ├── markdown_export/# Note renderer, vault writer (3 export modes), front matter,
│   │                   #   folder template, semantics renderer, URL formatter
│   ├── review/         # Review payload builder, confidence flagging, correction service
│   └── storage/        # SQLite engine, db_models, artifact registry, run_logger,
│                       #   vault_config persistence
│
├── samples/            # Development sample notebook page images
├── tests/
│   ├── golden/         # Golden fixtures per content type (layout, OCR, tables, diagrams)
│   └── test_pipeline_integration.py
└── docs/               # This file; architecture.md; pointer to quickstart
```
