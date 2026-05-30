"""Post-processing of raw VLM Markdown: arrows, repetition loops, mermaid sanitising."""

from __future__ import annotations

import re

from .mermaid import close_dangling_fence, sanitize_mermaid_blocks, unwrap_outer_fence

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
    (re.compile(r"\bestas\b"), "estas"),
    (re.compile(r"\be\b +"), ""),  # stray 'e' before words
    (re.compile(r"^\|\s*$", re.MULTILINE), ""),  # stray lone pipe on empty line
]

# Stray code fence cleanup — VLM sometimes wraps output in ```markdown despite instructions
_STRAY_FENCE = re.compile(r"^```[a-z]*\s*$", re.MULTILINE)

# Common VLM misread fix-ups for Spanish business notes
_VLM_FIXUPS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bestrategi\b", re.IGNORECASE), "estrategia"),
    (re.compile(r"\bEstrategi\b", re.IGNORECASE), "Estrategia"),
    (re.compile(r"\bestategia\b", re.IGNORECASE), "estrategia"),
    (re.compile(r"\bEstategia\b", re.IGNORECASE), "Estrategia"),
    (re.compile(r"\bcompetitiv\b", re.IGNORECASE), "competitivo"),
    (re.compile(r"\bdiferenciaci\b", re.IGNORECASE), "diferenciación"),
    (re.compile(r"\bposicionamient\b", re.IGNORECASE), "posicionamiento"),
    (re.compile(r"\bsegmentaci\b", re.IGNORECASE), "segmentación"),
    (re.compile(r"\btransformaci\b", re.IGNORECASE), "transformación"),
    (re.compile(r"\borganizaci\b", re.IGNORECASE), "organización"),
    (re.compile(r"\bplanificaci\b", re.IGNORECASE), "planificación"),
    (re.compile(r"\bimplementaci\b", re.IGNORECASE), "implementación"),
    (re.compile(r"\bevaluaci\b", re.IGNORECASE), "evaluación"),
    (re.compile(r"\bauditori\b", re.IGNORECASE), "auditoría"),
    (re.compile(r"\bproducci\b", re.IGNORECASE), "producción"),
    (re.compile(r"\boperaci\b", re.IGNORECASE), "operación"),
    (re.compile(r"\bparticipaci\b", re.IGNORECASE), "participación"),
    (re.compile(r"\bcomerciali\b", re.IGNORECASE), "comercial"),
    (re.compile(r"\bmercad\b(?![a-záéíóú])", re.IGNORECASE), "mercado"),
    (re.compile(r"\bnegoci\b", re.IGNORECASE), "negocio"),
    (re.compile(r"\bempresari\b", re.IGNORECASE), "empresarial"),
    (re.compile(r"\bexpansi\b", re.IGNORECASE), "expansión"),
    (re.compile(r"\bdirecci\b", re.IGNORECASE), "dirección"),
    (re.compile(r"\badminstraci\b", re.IGNORECASE), "administración"),
    (re.compile(r"\binformaci\b", re.IGNORECASE), "información"),
    (re.compile(r"\btádico\b", re.IGNORECASE), "táctico"),
    (re.compile(r"\bmetodo\b", re.IGNORECASE), "método"),
    (re.compile(r"\bmetricon\b", re.IGNORECASE), "métricas"),
    (re.compile(r"\bvision\b", re.IGNORECASE), "visión"),
    (re.compile(r"\bgestion\b", re.IGNORECASE), "gestión"),
    (re.compile(r"\bobjetiv\b", re.IGNORECASE), "objetivo"),
    (re.compile(r"\bposicionami\b", re.IGNORECASE), "posicionamiento"),
    (re.compile(r"\bventaj\b", re.IGNORECASE), "ventaja"),
    (re.compile(r"\bcompetenci\b", re.IGNORECASE), "competencia"),
    (re.compile(r"\bdiferenciad\b", re.IGNORECASE), "diferenciada"),
    (re.compile(r"\bespecifíc\b", re.IGNORECASE), "específica"),
    (re.compile(r"\bcompetitiv\b", re.IGNORECASE), "competitivo"),
    (re.compile(r"\bespecializad\b", re.IGNORECASE), "especializado"),
    (re.compile(r"\bintensiv\b", re.IGNORECASE), "intensiva"),
    (re.compile(r"\bgeográfic\b", re.IGNORECASE), "geográfico"),
    (re.compile(r"\bcorporativ\b", re.IGNORECASE), "corporativa"),
    (re.compile(r"\bfuncional\b", re.IGNORECASE), "funcional"),
    (re.compile(r"\bestructur\b", re.IGNORECASE), "estructura"),
]


def collapse_repetitions(text: str) -> str:
    """Remove VLM repetition loops.

    Vision models occasionally loop, emitting the same short block of lines over and
    over (e.g. ``Plan de IT / --> / Plan de`` repeated 11×). This collapses any block of
    1–8 lines that repeats 3+ times consecutively to a single occurrence, and drops runs
    of identical adjacent lines.
    """
    lines = text.splitlines()
    for size in range(1, 9):
        out: list[str] = []
        i = 0
        n = len(lines)
        while i < n:
            block = lines[i : i + size]
            if len(block) == size:
                reps = 1
                j = i + size
                while lines[j : j + size] == block:
                    reps += 1
                    j += size
                if reps >= 3:
                    out.extend(block)
                    i = j
                    continue
            out.append(lines[i])
            i += 1
        lines = out
    deduped: list[str] = []
    for ln in lines:
        if ln.strip() and deduped and deduped[-1] == ln:
            continue
        deduped.append(ln)
    return "\n".join(deduped)


# Outer language-fence marker (e.g. opening ```markdown) — VLM sometimes wraps despite instructions.
_OPEN_FENCE = re.compile(r"^```[a-zA-Z0-9_+#-]*\s*", re.MULTILINE)
_CLOSE_FENCE = re.compile(r"\s*```\s*$", re.MULTILINE)


def _strip_outer_fence(text: str) -> str:
    """Aggressively strip an outer ```lang ... ``` wrapper that wraps the entire text.

    This is a more robust fallback after ``unwrap_outer_fence``. It handles cases where
    the closing fence is on the same line as content or where there are multiple fences.
    """
    # First try the precise unwrapper (preserves inner fences)
    result = unwrap_outer_fence(text)
    # If the result still starts with a code fence marker, strip it more aggressively
    while re.match(r"^```[a-zA-Z0-9_+#-]*", result.strip()):
        lines = result.splitlines()
        if not lines:
            break
        # Remove first line if it's a fence opener
        if re.match(r"^```[a-zA-Z0-9_+#-]*\s*$", lines[0]):
            lines = lines[1:]
        # Remove last line if it's a fence closer
        if lines and re.match(r"^\s*```\s*$", lines[-1]):
            lines = lines[:-1]
        result = "\n".join(lines).strip()
    return result


def post_process(text: str) -> str:
    """Clean a raw VLM transcription into final Markdown."""
    text = _strip_outer_fence(text)
    for pattern, replacement in _ARROW_FIX:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _HALLUCINATION_PATTERNS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _VLM_FIXUPS:
        text = pattern.sub(replacement, text)
    text = _NUMBERED_REFORMAT.sub(lambda m: f"{m.group(1)} . ", text)
    text = sanitize_mermaid_blocks(close_dangling_fence(text))
    text = collapse_repetitions(text)
    # Final pass: remove any remaining stray code fence lines that are NOT part of mermaid blocks
    # (mermaid blocks were already processed above; any remaining fences are non-mermaid stowaways)
    text = _STRAY_FENCE.sub("", text)
    return text.strip()
