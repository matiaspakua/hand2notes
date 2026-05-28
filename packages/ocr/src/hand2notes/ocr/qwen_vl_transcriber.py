"""Qwen2.5-VL transcriber via Ollama — primary VLM for handwriting recognition.

Qwen2.5-VL is purpose-built for document understanding and outperforms gemma4
on handwritten multilingual content. Preferred over gemma4 when available.

Falls back gracefully when the model is not installed.
"""

import base64
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_MODEL_NAMES = ["qwen2.5vl:7b", "qwen2.5-vl:7b", "qwen2.5vl:latest", "qwen2.5-vl:latest"]
_TIMEOUT = 180.0

_TRANSCRIPTION_PROMPT = (
    "You are an expert OCR system for handwritten university notes.\n\n"
    "Carefully read EVERY word in the image and transcribe it as structured Markdown.\n"
    "The page is written in Spanish. Preserve all Spanish characters exactly.\n\n"
    "STRUCTURE RULES:\n"
    "- The main titles at the top (underlined or highlighted) → use `# Title` (one `#` per title line)\n"
    "- Section labels like `1)` or `2)` → keep as plain text, never use `##` headings\n"
    "- After a section label, preserve any connector block on the next lines unchanged\n"
    "- Arrows: write as `-->` or `--->` (NEVER Unicode → or LaTeX \\rightarrow)\n"
    "- A vertical bar `|` used as a connector → stays on its own line with the same indentation\n\n"
    "TABLE RULES (for any grid/table visible in the image):\n"
    "- Use standard Markdown: `| col1 | col2 | col3 |`\n"
    "- Separator row uses only dashes: `| --- | --- | --- |`\n"
    "- Empty cells: `|  |`\n\n"
    "LIST RULES:\n"
    "- Numbered items: `N . text` format (digit SPACE dot SPACE text)\n"
    "- Bulleted items: `- text`\n\n"
    "SPATIAL LAYOUT:\n"
    "- Preserve indented/hierarchical connector trees using tabs\n"
    "- When two columns of text appear side by side at the bottom, preserve spacing\n\n"
    "IGNORE: dates, page numbers, and timestamps in margins/corners.\n\n"
    "Output raw Markdown ONLY. No code fences, no explanation, no preamble."
)

_ARROW_FIX = [
    (re.compile(r"\$\\rightarrow\$"), "-->"),
    (re.compile(r"\\rightarrow"), "-->"),
    (re.compile(r"→"), "-->"),
    (re.compile(r"←"), "<--"),
    (re.compile(r"-→"), "-->"),
]

_NUMBERED_REFORMAT = re.compile(r"^(\d+)\.\s+", re.MULTILINE)

_HALLUCINATION_PATTERNS = [
    (re.compile(r"\bLa como se desdel\b\s*"), ""),
    (re.compile(r"\bLa cómo se\b\s*"), ""),
    (re.compile(r"\bdesdel\b"), "desde"),
]


def _post_process(text: str) -> str:
    for pattern, replacement in _ARROW_FIX:
        text = pattern.sub(replacement, text)
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    for pattern, replacement in _HALLUCINATION_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _NUMBERED_REFORMAT.sub(lambda m: f"{m.group(1)} . ", text)
    return text.strip()


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


def transcribe_page(
    image_path: Path,
    *,
    base_url: str = _DEFAULT_BASE_URL,
    timeout: float = _TIMEOUT,
) -> str:
    import httpx

    model = _find_model(base_url)
    if model is None:
        raise RuntimeError("No Qwen2.5-VL model found in Ollama")

    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": _TRANSCRIPTION_PROMPT,
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {"temperature": 0.0},
    }

    try:
        response = httpx.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"Qwen2.5-VL transcription failed: {exc}") from exc

    raw = response.json().get("message", {}).get("content", "")
    if not raw.strip():
        raise RuntimeError("Qwen2.5-VL returned empty transcription")

    log.debug("Qwen2.5-VL model=%s raw (%d chars): %s…", model, len(raw), raw[:120])
    return _post_process(raw)
