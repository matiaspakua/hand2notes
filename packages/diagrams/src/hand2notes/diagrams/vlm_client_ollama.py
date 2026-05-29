"""Ollama VLM client for diagram interpretation.

Sends a diagram crop to qwen2.5vl:7b via the Ollama HTTP API and requests
constrained JSON output describing nodes, edges, diagram type, and confidence.
"""

import base64
import json
import logging
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5vl:7b"

_SYSTEM_PROMPT = (
    "You are a diagram interpreter. Analyze the provided image of a hand-drawn diagram "
    "and return a JSON object with exactly these fields: "
    '"type" (one of: flowchart, sequence, uml_class, uml_activity, block_diagram, '
    "architecture, graph_network, annotated_sketch, chart_plot, unknown), "
    '"confidence" (float 0.0–1.0), '
    '"nodes" (array of {id, label, node_type}), '
    '"edges" (array of {source_id, target_id, label, direction}). '
    "Return ONLY valid JSON, no markdown, no explanation."
)


def interpret_diagram(
    image_path: Path,
    *,
    base_url: str = _DEFAULT_BASE_URL,
    model: str = _DEFAULT_MODEL,
    timeout: float = 60.0,
) -> dict:
    """Send a diagram crop to Ollama and return raw constrained JSON dict.

    Raises RuntimeError if the Ollama server is unreachable or returns an error.
    """
    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Interpret this diagram:",
                "images": [image_b64],
            },
        ],
        "stream": False,
        "format": "json",
        # Bounded context: an unbounded num_ctx makes Ollama allocate a ~35 GiB
        # compute graph that segfaults the runner on CPU-only hosts.
        "options": {"temperature": 0.0, "num_ctx": 8192, "num_predict": 1024},
    }

    try:
        response = httpx.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.ConnectError as exc:
        raise RuntimeError(f"Ollama server not reachable at {base_url}") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.response.status_code}") from exc

    body = response.json()
    content = body.get("message", {}).get("content", "")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        log.warning("Ollama returned non-JSON content: %s", content[:200])
        raise RuntimeError(f"Ollama response was not valid JSON: {exc}") from exc
