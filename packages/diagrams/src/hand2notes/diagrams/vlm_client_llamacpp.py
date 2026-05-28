"""llama.cpp VLM client for diagram interpretation.

Loads a GGUF model via llama-cpp-python and interprets diagram crops using the
same constrained JSON contract as the Ollama client.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

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

# Module-level model cache so repeated calls reuse the loaded model.
_model_cache: dict[str, object] = {}


def _load_model(model_path: str) -> object:
    if model_path in _model_cache:
        return _model_cache[model_path]

    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("llama-cpp-python is not installed") from exc

    log.info("Loading GGUF model from %s", model_path)
    model = Llama(
        model_path=model_path,
        n_ctx=4096,
        n_gpu_layers=-1,  # offload all layers to GPU when available
        verbose=False,
    )
    _model_cache[model_path] = model
    return model


def interpret_diagram(
    image_path: Path,
    *,
    model_path: str,
    max_tokens: int = 1024,
) -> dict:
    """Interpret a diagram crop via llama-cpp-python and return constrained JSON dict.

    Args:
        image_path: Path to the cropped diagram image.
        model_path: Path to the GGUF model file.
        max_tokens: Maximum tokens for the JSON response.

    Raises RuntimeError if the model cannot be loaded or returns invalid JSON.
    """
    try:
        import base64

        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError("llama-cpp-python is not installed") from exc

    model = _load_model(model_path)

    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Interpret this diagram:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        },
    ]

    try:
        result = model.create_chat_completion(  # type: ignore[union-attr]
            messages=messages,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected llama-cpp response structure: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"llama-cpp returned non-JSON content: {exc}") from exc
