# API Contract: Session Management

**Base URL**: `http://localhost:{port}/api/v1`
**Transport**: HTTP/1.1 JSON REST
**Auth**: None (local-only, single-user desktop app)

---

## POST /sessions

Create a new session.

**Request body**:
```json
{
  "name": "string",
  "notebook": "string",
  "topic": "string | null",
  "tags": ["string"],
  "export_mode": "overwrite | versioned | merge"
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "name": "string",
  "notebook": "string",
  "topic": "string | null",
  "status": "created",
  "created_at": "ISO8601",
  "pages": [],
  "tags": ["string"]
}
```

---

## POST /sessions/{session_id}/pages

Add one or more ordered page images to a session.

**Request**: `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `files` | `File[]` | Image files (JPG, PNG, HEIC) |
| `sequence_start` | `int` | 1-based starting index for these pages (default: next available) |

**Response 201**:
```json
{
  "added": [
    {
      "id": "uuid",
      "sequence": 1,
      "source_path": "string",
      "width_px": 3024,
      "height_px": 4032,
      "pipeline_stage": "import",
      "review_status": "pending"
    }
  ]
}
```

**Errors**:
- `400` — unsupported file format
- `413` — file too large (> 50 MB per file)

---

## GET /sessions/{session_id}

Get full session state including all pages and blocks.

**Response 200**: Full Session object (see data-model.md).

**Errors**:
- `404` — session not found

---

## PATCH /sessions/{session_id}

Update session metadata (name, notebook, topic, tags).

**Request body** (all fields optional):
```json
{
  "name": "string",
  "notebook": "string",
  "topic": "string | null",
  "tags": ["string"]
}
```

**Response 200**: Updated Session object.

---

## PATCH /sessions/{session_id}/pages/reorder

Reorder pages within a session.

**Request body**:
```json
{
  "page_ids": ["uuid", "uuid", "uuid"]
}
```
Order of IDs defines new 1-based sequence.

**Response 200**:
```json
{ "reordered": true, "page_count": 3 }
```

---

## DELETE /sessions/{session_id}

Delete a session and all derived data. Does NOT delete vault export artifacts.

**Response 204**: No content.

---

## GET /sessions

List all sessions, most recent first.

**Query params**:

| Param | Type | Description |
|-------|------|-------------|
| `status` | `string` | Filter by SessionStatus |
| `notebook` | `string` | Filter by notebook name |
| `limit` | `int` | Max results (default 50) |
| `offset` | `int` | Pagination offset |

**Response 200**:
```json
{
  "sessions": [ /* Session summary objects */ ],
  "total": 12
}
```
