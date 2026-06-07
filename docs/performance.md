# Performance

## Model Caching Strategy

Heavy ML models (Surya layout detector and ordering model) are loaded at most once
per process via module-level caching:

- **`detector.py`**: `_get_predictor()` creates a singleton `LayoutPredictor` on
  first call and reuses it for all subsequent pages. This avoids the ~2–3s overhead
  of model initialization per page.
- **`reading_order.py`**: `_get_models()` creates singleton ordering model and
  processor instances, reused across all pages in a batch.

## VLM Transcription

Qwen2.5-VL runs a two-pass transcription:
1. **Text pass**: Transcribes all visible text as structured Markdown.
2. **Diagram pass**: Scans for hand-drawn diagrams and outputs Mermaid flowchart
   code blocks if found, or `NONE` otherwise.

## Typical Latency (per A4 page)

| Stage               | Time (approx) |
|---------------------|---------------|
| Surya layout detect | 0.5–1s        |
| Surya reading order | 0.3–0.8s      |
| VLM text pass       | 3–8s          |
| VLM diagram pass    | 2–5s          |
| **Total**           | **6–15s**     |

*Times are measured on Apple Silicon (M-series) hardware with GPU acceleration
enabled.*
