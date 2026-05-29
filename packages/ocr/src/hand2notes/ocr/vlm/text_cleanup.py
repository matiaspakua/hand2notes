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


def post_process(text: str) -> str:
    """Clean a raw VLM transcription into final Markdown."""
    text = unwrap_outer_fence(text)
    for pattern, replacement in _ARROW_FIX:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _HALLUCINATION_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _NUMBERED_REFORMAT.sub(lambda m: f"{m.group(1)} . ", text)
    text = sanitize_mermaid_blocks(close_dangling_fence(text))
    text = collapse_repetitions(text)
    return text.strip()
