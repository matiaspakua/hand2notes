# Quickstart: hand2notes Development Setup

**Date**: 2026-05-27
**Plan**: [plan.md](./plan.md)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20 LTS+ | Electron + React frontend |
| uv | latest | Python package/project manager |
| pnpm | 8+ | Node package manager |
| Ollama | latest | Local VLM (developer convenience runtime) |
| llama.cpp | latest | Local VLM (production runtime) |
| PlantUML | 1.2024+ | Diagram rendering for previews |
| Java | 11+ | Required by PlantUML |

---

## Repository Structure

```
hand2notes/
├── apps/
│   ├── electron-ui/    ← TypeScript / Electron frontend
│   └── python-api/     ← Python / FastAPI backend
├── packages/           ← Python packages (core_models, ocr, layout, …)
├── specs/              ← Feature specifications and plans
└── tests/golden/       ← Golden fixture images and expected outputs
```

---

## Backend Setup

```bash
# From repo root
cd apps/python-api

# Install dependencies (uv recommended)
uv sync

# Run database migrations (SQLite, auto-created on first run)
uv run alembic upgrade head

# Start the API server (development mode)
uv run uvicorn hand2notes.api.main:app --reload --port 7432
```

The API will be available at `http://localhost:7432`.
Interactive docs at `http://localhost:7432/docs`.

---

## Frontend Setup

```bash
# From repo root
cd apps/electron-ui

# Install dependencies
pnpm install

# Start the Electron app (development mode, connects to localhost:7432)
pnpm dev
```

The Electron app starts automatically and connects to the running Python API.
The React renderer hot-reloads on file changes.

---

## VLM Setup (Diagram Interpreter)

### Option A — Ollama (developer convenience)

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5vl:7b       # ~6 GB download
ollama serve                    # starts on port 11434
```

Set in app config: `vlm_runtime = "ollama"`, `vlm_model = "qwen2.5vl:7b"`.

### Option B — llama.cpp (production default)

```bash
# Download GGUF model
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-GGUF \
  qwen2_5vl-7b-instruct-q4_k_m.gguf --local-dir ./models/

# llama-cpp-python is installed as part of python-api dependencies
# Point config to GGUF path
```

Set in app config: `vlm_runtime = "llamacpp"`, `vlm_model = "./models/qwen2_5vl-7b-instruct-q4_k_m.gguf"`.

---

## Running Tests

```bash
# Python backend unit + integration tests
cd apps/python-api
uv run pytest tests/ -v

# Golden fixture regression tests only
uv run pytest tests/golden/ -v --tb=short

# TypeScript / Electron renderer tests
cd apps/electron-ui
pnpm test
```

---

## Adding a Golden Fixture

1. Create a directory under `tests/golden/<category>/<fixture-name>/`
2. Add the input image: `input.jpg`
3. Add the expected output: `expected-*.md` / `expected-*.json` / `expected-*.puml`
4. Write a pytest test in `tests/golden/<category>/test_<fixture_name>.py` that
   calls the relevant pipeline stage with `input.jpg` and asserts against the expected output.

---

## Configuration

The app config is stored at `~/.config/hand2notes/config.json` (Linux/macOS) or
`%APPDATA%\hand2notes\config.json` (Windows). Edit via Settings screen in the UI
or via `PUT /api/v1/config`.

Minimum required config to start processing:
```json
{
  "vault_root": "/path/to/your/ObsidianVault",
  "vlm_runtime": "ollama",
  "vlm_model": "qwen2.5vl:7b"
}
```

---

## API Quick Reference

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/sessions` | Create a new note session |
| `POST /api/v1/sessions/{id}/pages` | Upload page images |
| `POST /api/v1/sessions/{id}/process` | Run the full pipeline |
| `WS /api/v1/sessions/{id}/progress` | Stream pipeline progress |
| `GET /api/v1/sessions/{id}/pages/{pid}/review` | Get review data |
| `POST /api/v1/sessions/{id}/export` | Export to Obsidian vault |
| `GET /api/v1/config` | Get / update configuration |

Full contract details: [session-api.md](./contracts/session-api.md),
[pipeline-api.md](./contracts/pipeline-api.md), [config-api.md](./contracts/config-api.md)
