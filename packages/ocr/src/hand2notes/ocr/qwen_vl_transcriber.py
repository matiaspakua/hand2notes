"""Qwen2.5-VL transcriber via Ollama — primary VLM for handwriting recognition.

Qwen2.5-VL is purpose-built for document understanding and outperforms gemma4 on
handwritten multilingual content. Preferred over gemma4 when available.

This module is a thin orchestrator: prompts, Mermaid sanitising, text cleanup and the
transcription cache live in the ``vlm`` subpackage so each concern stays small and
testable. Transcription is two-pass — a reliable text pass plus a focused, best-effort
diagram pass — with an on-disk cache so repeated runs return in milliseconds.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from .vlm import cache, mermaid
from .vlm.prompts import DIAGRAM_PROMPT, TRANSCRIPTION_PROMPT
from .vlm.text_cleanup import collapse_repetitions, post_process

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_MODEL_NAMES = ["qwen2.5vl:7b", "qwen2.5-vl:7b", "qwen2.5vl:latest", "qwen2.5-vl:latest"]
_TIMEOUT = 180.0

# Generation options. ``num_ctx`` MUST be bounded: Qwen2.5-VL's native context is 128k,
# and leaving it unbounded makes Ollama allocate a ~35 GiB compute graph that segfaults
# the runner. 8192 fits a full page's vision + text tokens with a small, fast kv-cache.
# ``num_predict`` caps runaway generation — a page needs < 1024 tokens.
_NUM_CTX = 8192
_NUM_PREDICT = 1024
_OPTIONS = {
    "temperature": 0.0,
    "num_ctx": _NUM_CTX,
    "num_predict": _NUM_PREDICT,
}

# Images are downscaled to this longest edge before being sent to Ollama. 1280px is the
# sweet spot: above it the vision-token count balloons AND the model tends to over-
# generate / loop, while quality plateaus. At 1280px transcription is concise and fast
# (~4s warm) with the same word-recall (~87%).
_MAX_IMAGE_EDGE = 1280


def _find_model(base_url: str) -> str | None:
    """Return the first available Qwen2.5-VL model name, or None."""
    try:
        import httpx

        r = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if r.status_code != 200:
            return None
        available = [m.get("name", "") for m in r.json().get("models", [])]
        for candidate in _MODEL_NAMES:
            base = candidate.split(":")[0]
            if any(m.startswith(base) for m in available):
                return candidate
        return None
    except Exception:
        return None


def is_available(base_url: str = _DEFAULT_BASE_URL) -> bool:
    return _find_model(base_url) is not None


def _encode_image(image_path: Path) -> str:
    """Return base64 JPEG bytes, downscaling oversized images first.

    Guards against the runner-crashing vision-token explosion that occurs when a
    full-resolution phone photo is sent directly.
    """
    raw = image_path.read_bytes()
    try:
        from PIL import Image as PILImage

        with PILImage.open(io.BytesIO(raw)) as img:
            w, h = img.size
            longest = max(w, h)
            if longest > _MAX_IMAGE_EDGE:
                scale = _MAX_IMAGE_EDGE / longest
                img = img.convert("RGB").resize(
                    (int(w * scale), int(h * scale)), PILImage.LANCZOS
                )
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=90)
                raw = buf.getvalue()
                log.info(
                    "Downscaled oversized image %s (%dx%d → longest %d) before VLM send",
                    image_path.name, w, h, _MAX_IMAGE_EDGE,
                )
    except Exception as exc:  # noqa: BLE001 — never block transcription on resize
        log.debug("Image guard skipped for %s: %s", image_path.name, exc)
    return base64.b64encode(raw).decode("utf-8")


def _chat(model: str, prompt: str, image_b64: str, base_url: str, timeout: float) -> str:
    import httpx

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
        "stream": False,
        "options": _OPTIONS,
    }
    response = httpx.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "")


def _diagram_blocks(model: str, image_b64: str, base_url: str, timeout: float) -> str:
    """Run the focused diagram pass; return sanitised ```mermaid blocks (or "")."""
    try:
        raw = _chat(model, DIAGRAM_PROMPT, image_b64, base_url, timeout)
    except Exception as exc:  # noqa: BLE001 — diagrams are best-effort; never block text
        log.warning("Diagram pass failed: %s", exc)
        return ""
    if not raw.strip() or raw.strip().upper().startswith("NONE"):
        return ""
    cleaned = mermaid.sanitize_mermaid_blocks(mermaid.close_dangling_fence(raw))
    blocks = mermaid.MERMAID_FENCE_RE.findall(cleaned)
    return "\n\n".join(f"```mermaid\n{b.strip()}\n```" for b in blocks if b.strip())


def _cache_key(image_b64: str, include_diagrams: bool) -> str:
    import json

    return cache.cache_key(
        json.dumps(_OPTIONS, sort_keys=True),
        TRANSCRIPTION_PROMPT,
        DIAGRAM_PROMPT if include_diagrams else "",
        image_b64,
    )


def transcribe_page(
    image_path: Path,
    *,
    base_url: str = _DEFAULT_BASE_URL,
    timeout: float = _TIMEOUT,
    include_diagrams: bool = True,
) -> str:
    model = _find_model(base_url)
    if model is None:
        raise RuntimeError("No Qwen2.5-VL model found in Ollama")

    image_b64 = _encode_image(image_path)

    key = _cache_key(image_b64, include_diagrams)
    cached = cache.cache_get(key)
    if cached is not None:
        log.info("VLM cache hit for %s — returning cached transcription", image_path.name)
        return cached

    # Pass 1: full text transcription (reliable, no diagram instructions).
    try:
        raw = _chat(model, TRANSCRIPTION_PROMPT, image_b64, base_url, timeout)
    except Exception as exc:
        raise RuntimeError(f"Qwen2.5-VL transcription failed: {exc}") from exc
    if not raw.strip():
        raise RuntimeError("Qwen2.5-VL returned empty transcription")

    text = post_process(raw)

    # Pass 2: focused diagram extraction, appended after the text. Best-effort.
    if include_diagrams:
        diagrams = _diagram_blocks(model, image_b64, base_url, timeout)
        if diagrams:
            log.info("Diagram pass produced %d mermaid block(s)", diagrams.count("```mermaid"))
            text = f"{text}\n\n{diagrams}"

    cache.cache_put(key, text)
    log.debug("Qwen2.5-VL model=%s text (%d chars)", model, len(text))
    return text


# ── Backward-compatible private aliases (referenced by existing tests) ────────
_TRANSCRIPTION_PROMPT = TRANSCRIPTION_PROMPT
_DIAGRAM_PROMPT = DIAGRAM_PROMPT
_collapse_repetitions = collapse_repetitions
_post_process = post_process
_sanitize_mermaid_blocks = mermaid.sanitize_mermaid_blocks
_unwrap_outer_fence = mermaid.unwrap_outer_fence
_close_dangling_fence = mermaid.close_dangling_fence
_cache_dir = cache.cache_dir
_cache_enabled = cache.cache_enabled
_cache_get = cache.cache_get
_cache_put = cache.cache_put
