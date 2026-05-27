# API Contract: Configuration

**Base URL**: `http://localhost:{port}/api/v1`

---

## GET /config

Get the current application configuration.

**Response 200**:
```json
{
  "vault_root": "/Users/matias/Documents/ObsidianVault | null",
  "folder_template": "{{notebook}}/{{date}}-{{topic}}",
  "export_mode": "overwrite",
  "default_notebook": "Engineering | null",
  "vlm_runtime": "llamacpp | ollama",
  "vlm_model": "qwen2.5vl:7b",
  "ocr_languages": ["es", "en"],
  "confidence_threshold": 0.65,
  "front_matter_fields": {
    "created": "{{date}}",
    "tags": "{{tags}}",
    "source": "hand2notes"
  }
}
```

---

## PUT /config

Replace the full configuration.

**Request body**: Same shape as GET /config response. All fields required.

**Response 200**: Updated config object.

**Errors**:
- `422` — invalid vault path (directory does not exist or is not writable)
- `422` — invalid folder template (Jinja2 syntax error)

---

## PATCH /config

Partial configuration update.

**Request body**: Any subset of config fields.

**Response 200**: Updated config object.

---

## GET /config/vault/validate

Validate that the configured vault path is accessible and writable.

**Response 200**:
```json
{
  "valid": true,
  "vault_root": "/Users/matias/Documents/ObsidianVault",
  "writable": true,
  "existing_notes_count": 342
}
```

**Response 200** (invalid):
```json
{
  "valid": false,
  "vault_root": "/invalid/path",
  "error": "Path does not exist"
}
```

---

## GET /config/vlm/status

Check the status of the configured VLM runtime and model.

**Response 200**:
```json
{
  "runtime": "llamacpp",
  "model": "qwen2.5vl:7b",
  "available": true,
  "model_size_gb": 6.1,
  "backend_info": "METAL (Apple Silicon)"
}
```

**Response 200** (not available):
```json
{
  "runtime": "ollama",
  "model": "qwen2.5vl:7b",
  "available": false,
  "error": "Ollama daemon not running"
}
```
