# API Contract: Pipeline Processing

**Base URL**: `http://localhost:{port}/api/v1`
**Transport**: HTTP/1.1 JSON REST + WebSocket for streaming progress

---

## POST /sessions/{session_id}/process

Start the full pipeline for a session (all stages in sequence).

**Request body**:
```json
{
  "stages": ["preprocess", "detect_layout", "recognize_text",
             "reconstruct_structure", "detect_diagrams", "generate_output"],
  "options": {
    "ocr_languages": ["es", "en"],
    "vlm_enabled": true,
    "confidence_threshold": 0.65
  }
}
```
`stages` defaults to all stages. Use the single-stage endpoint to run one at a time.

**Response 202**:
```json
{
  "run_id": "uuid",
  "session_id": "uuid",
  "status": "running",
  "stages_queued": ["preprocess", "detect_layout", "recognize_text",
                    "reconstruct_structure", "detect_diagrams", "generate_output"]
}
```

---

## POST /sessions/{session_id}/stages/{stage}

Run a single pipeline stage. Useful for re-processing or debugging.

**Path param `stage`**: one of `preprocess` | `detect_layout` | `recognize_text` |
`reconstruct_structure` | `detect_diagrams` | `generate_output`

**Response 202**:
```json
{
  "run_id": "uuid",
  "stage": "preprocess",
  "status": "running"
}
```

**Errors**:
- `409` — session already has an active run in progress
- `422` — prerequisite stage not yet completed

---

## GET /sessions/{session_id}/runs/{run_id}

Get the status and metrics of a pipeline run.

**Response 200**:
```json
{
  "id": "uuid",
  "session_id": "uuid",
  "stage": "detect_layout",
  "started_at": "ISO8601",
  "completed_at": "ISO8601 | null",
  "status": "running | completed | failed | cancelled",
  "error": "string | null",
  "metrics": {
    "pages_processed": 2,
    "blocks_detected": 14,
    "confidence_mean": 0.82
  },
  "progress": {
    "current_page": 2,
    "total_pages": 5,
    "percent": 40
  }
}
```

---

## POST /sessions/{session_id}/runs/{run_id}/cancel

Cancel an active pipeline run.

**Response 200**:
```json
{ "cancelled": true }
```

**Errors**:
- `409` — run already completed or failed

---

## WebSocket /sessions/{session_id}/progress

Real-time pipeline progress stream.

**Connect**: `ws://localhost:{port}/api/v1/sessions/{session_id}/progress`

**Server sends** (JSON frames):
```json
{
  "event": "stage_started | stage_completed | stage_failed | page_processed | block_detected | run_completed",
  "stage": "string",
  "page_id": "uuid | null",
  "block_id": "uuid | null",
  "confidence": 0.87,
  "message": "string",
  "progress_percent": 45,
  "timestamp": "ISO8601"
}
```

---

## GET /sessions/{session_id}/pages/{page_id}/review

Get the review payload for a single page: original image URL, blocks with
confidence scores, Markdown preview, and diagram previews.

**Response 200**:
```json
{
  "page_id": "uuid",
  "sequence": 1,
  "original_image_url": "/static/crops/{page_id}/original.jpg",
  "preprocessed_image_url": "/static/crops/{page_id}/preprocessed.jpg",
  "blocks": [
    {
      "id": "uuid",
      "block_type": "heading",
      "reading_order": 0,
      "bbox": { "x": 120, "y": 45, "width": 800, "height": 60 },
      "confidence": 0.91,
      "review_flag": false,
      "content": "System Architecture Overview",
      "corrected_content": null,
      "visual_semantics": null
    }
  ],
  "markdown_preview": "# System Architecture Overview\n\n...",
  "diagram_previews": [
    {
      "block_id": "uuid",
      "diagram_type": "flowchart",
      "crop_url": "/static/crops/{block_id}/diagram.jpg",
      "generated_source_url": "/static/artifacts/{block_id}/diagram.puml",
      "reconstruction_confidence": 0.78,
      "review_decision": "pending"
    }
  ],
  "overall_confidence": 0.84,
  "review_status": "in_review"
}
```

---

## PATCH /sessions/{session_id}/pages/{page_id}/blocks/{block_id}

Apply a user correction to a block.

**Request body**:
```json
{
  "corrected_content": "string | null",
  "review_flag": false
}
```

**Response 200**: Updated Block object.

---

## PATCH /sessions/{session_id}/pages/{page_id}/diagrams/{block_id}

Set the review decision for a diagram block.

**Request body**:
```json
{
  "review_decision": "approved | rejected | deferred"
}
```

**Response 200**: Updated DiagramBlock object.

---

## POST /sessions/{session_id}/export

Trigger export to the Obsidian vault after review.

**Request body**:
```json
{
  "export_mode": "overwrite | versioned | merge",
  "vault_subfolder": "string | null"
}
```
`vault_subfolder` overrides the VaultConfig template for this export only.

**Response 202**:
```json
{
  "export_run_id": "uuid",
  "status": "running",
  "vault_path": "string"
}
```

---

## GET /sessions/{session_id}/export/status

Get the export run status.

**Response 200**:
```json
{
  "export_run_id": "uuid",
  "status": "running | completed | failed",
  "artifacts_written": [
    { "type": "markdown", "vault_relative_path": "Engineering/2026-05-27-arch/notes.md" },
    { "type": "plantuml", "vault_relative_path": "Engineering/2026-05-27-arch/diagrams/001-arch.puml" }
  ],
  "error": "string | null"
}
```
