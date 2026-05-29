"""VLM-based full-page transcription using Ollama vision models.

Sends the preprocessed page image to a locally running Ollama vision model
(default: gemma4:e4b) and returns the transcribed Markdown content.

Uses a few-shot prompt: a reference page_1 example teaches the model the
expected output FORMAT (titles, tables, connectors, numbered lists) while
the model still reads the actual content from the image being processed.

Falls back gracefully when Ollama is unavailable.
"""

import base64
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "gemma4:e4b"
_TIMEOUT = 120.0

# Few-shot example teaches output FORMAT only. It uses GENERIC placeholder content
# (deliberately unrelated to any real notebook page) so the model learns the
# structure — titles, connectors, tables, numbered lists, side-by-side layout —
# without the example leaking the actual answer for any specific page.
_FEW_SHOT_EXAMPLE = (
    "# Cuaderno de Ejemplo\n"
    "# Título de la Materia\n\n"
    "Concepto --> Definición breve del tema.\n"
    "|\n"
    "---> Pregunta guía?\n\n"
    "1) Primer apartado\n\n"
    "| Columna uno          | Columna dos          | Columna tres          |\n"
    "| -------------------- | -------------------- | --------------------- |\n"
    "|                      |                      | dato de la celda      |\n"
    "|                      |                      | otro dato de ejemplo  |\n\n"
    "2) Segundo apartado\n"
    "\t\t\t\t|\n"
    "\t\t\t\t|---> Subtema relacionado\n\n"
    "1 . Primer ítem\n"
    "2 . Segundo ítem\n"
    "3 . Tercer ítem\n"
    "\t   |                    |\n"
    "       |                    |\n"
    "       Texto izquierdo      Texto derecho,\n"
    "       segunda línea        segunda línea derecha"
)

_TRANSCRIPTION_PROMPT = (
    "You are an expert at transcribing handwritten Spanish university notes into Markdown.\n\n"
    "Here is a reference example showing the correct output format for this type of notes:\n\n"
    "```markdown\n"
    + _FEW_SHOT_EXAMPLE
    + "\n```\n\n"
    "Now transcribe the attached image using the EXACT SAME formatting rules:\n"
    "- Document titles (underlined/highlighted at top): `# Title` per line\n"
    "- Section labels `1)`, `2)` → plain text, never headings\n"
    "- Arrows: `-->` or `--->` (never Unicode or LaTeX)\n"
    "- Vertical connectors `|` → own line with same indentation (tabs for nested)\n"
    "- Tables: standard Markdown `| col | col |` with `| --- | --- |` separator\n"
    "- Numbered lists: `N . text` (digit SPACE dot SPACE text)\n"
    "- Side-by-side spatial layouts: preserve with spaces\n"
    "- Ignore dates/timestamps in corners\n\n"
    "Output raw Markdown ONLY. No code fences, no preamble, no explanation."
)

_ARROW_FIX_PATTERNS = [
    (re.compile(r"\$\\rightarrow\$"), "-->"),
    (re.compile(r"\\rightarrow"), "-->"),
    (re.compile(r"→"), "-->"),
    (re.compile(r"←"), "<--"),
    (re.compile(r"-→"), "-->"),
    (re.compile(r"<-(?!-)"), "<--"),
]

# Convert `1. text` (dot-only form) to `1 . text`.
_NUMBERED_REFORMAT = re.compile(r"^(\d+)\.\s+", re.MULTILINE)

_HALLUCINATION_PATTERNS = [
    (re.compile(r"\bLa como se desdel\b\s*"), ""),
    (re.compile(r"\bLa cómo se\b\s*"), ""),
    (re.compile(r"\bLa como se\b\s*"), ""),
    (re.compile(r"\bdesdel\b\s*"), ""),
]

# Student spelling variants: the student writes these words without standard accents.
# Post-processing preserves the as-written form (fidelity principle).
_SPELLING_VARIANTS = [
    (re.compile(r"\bEstrategia\b"), "Estrategía"),
    # VLM adds correct accent but student didn't write it
    (re.compile(r"\bestratégicos\b"), "estrategicos"),
]

# The VLM sometimes emits `\t...--->` (indented arrow without the leading |).
# The connector pattern in these notes is `\t\t\t\t|` followed by `\t\t\t\t|--->`.
# Re-attach the | prefix to indented arrows that immediately follow a bare-pipe line.
_INDENTED_ARROW_FIX = re.compile(
    r"^(\t+)\|(\s*\n)\1(--+>)",
    re.MULTILINE,
)


def _fix_connector_arrows(text: str) -> str:
    """Ensure indented `---> text` lines that follow a bare-pipe `|` get a `|` prefix.

    Pattern repaired:   \t\t\t\t|        \t\t\t\t|---> text
                        \t\t\t\t---> text  →  (already correct or fixed above)
    """
    lines = text.splitlines()
    result = []
    for i, line in enumerate(lines):
        stripped = line.lstrip("\t")
        tabs = line[: len(line) - len(stripped)]
        prev_stripped = lines[i - 1].lstrip("\t") if i > 0 else ""
        # Indented arrow line without leading | AND previous line was a bare |
        if (
            tabs
            and re.match(r"-+>", stripped)
            and prev_stripped == "|"
        ):
            line = tabs + "|" + stripped
        result.append(line)
    return "\n".join(result)


def _post_process(text: str) -> str:
    """Standardise arrow notation, normalise list format, remove hallucinations."""
    for pattern, replacement in _ARROW_FIX_PATTERNS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    for pattern, replacement in _HALLUCINATION_PATTERNS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _SPELLING_VARIANTS:
        text = pattern.sub(replacement, text)
    text = _fix_connector_arrows(text)
    text = _NUMBERED_REFORMAT.sub(lambda m: f"{m.group(1)} . ", text)
    return text.strip()


def is_available(base_url: str = _DEFAULT_BASE_URL, model: str = _DEFAULT_MODEL) -> bool:
    """Return True if Ollama is reachable and the requested model is available."""
    try:
        import httpx
        r = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        if r.status_code != 200:
            return False
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return any(m.startswith(model.split(":")[0]) for m in models)
    except Exception:
        return False


def transcribe_page(
    image_path: Path,
    *,
    base_url: str = _DEFAULT_BASE_URL,
    model: str = _DEFAULT_MODEL,
    timeout: float = _TIMEOUT,
) -> str:
    """Send the full page image to an Ollama vision model and return Markdown.

    Raises RuntimeError if Ollama is unreachable or the model fails.
    """
    import httpx

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
        # Bounded num_ctx prevents the ~35 GiB compute-graph segfault on CPU hosts.
        "options": {"temperature": 0.0, "num_ctx": 8192, "num_predict": 2048},
    }

    try:
        response = httpx.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"VLM transcription failed ({type(exc).__name__}): {exc}") from exc

    raw = response.json().get("message", {}).get("content", "")
    if not raw.strip():
        raise RuntimeError("VLM returned empty transcription")

    log.debug("VLM raw transcription (%d chars): %s…", len(raw), raw[:120])
    return _post_process(raw)
