"""Structure reconstructor: maps BlockType → Markdown elements."""

from __future__ import annotations

import re

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block

_BULLET_START = re.compile(r"^[\-\*\•·]\s*")
_NUMBERED_START = re.compile(r"^\s*(\d+)\s*[\.\)\-]\s*")
_ARROW_NORM = [
    (re.compile(r"-\s*>"), "→"),
    (re.compile(r"<\s*-"), "←"),
    (re.compile(r"\s+→\s+"), " → "),
    (re.compile(r"\s+←\s+"), " ← "),
]
_NOISE_RE = re.compile(r"^[·.·•\-–—=+|/\\]{1,3}$")


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _clean_line(text: str) -> str:
    t = text
    for pattern, repl in _ARROW_NORM:
        t = pattern.sub(repl, t)
    return t.strip()


def _is_noise(text: str) -> bool:
    return bool(_NOISE_RE.match(text.strip())) or len(text.strip()) < 2


def _lines_clean(text: str) -> list[str]:
    return [_clean_line(ln) for ln in _lines(text) if not _is_noise(ln)]


def _strip_leading_number(text: str) -> str:
    return re.sub(r"^\s*\d+[\s\.\-\)]+\s*", "", text).strip() or text


def _render_title(text: str) -> str:
    first = (_lines_clean(text) or [text])[0]
    return f"# {_strip_leading_number(first)}"


def _render_heading(text: str, level: int = 2) -> str:
    first = (_lines_clean(text) or [text])[0]
    return f"{'#' * level} {_strip_leading_number(first)}"


def _render_paragraph(text: str) -> str:
    lines = _lines_clean(text)
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    parts: list[str] = [lines[0]]
    for line in lines[1:]:
        prev = parts[-1]
        if prev.endswith("-"):
            parts[-1] = prev[:-1] + line
        elif prev.endswith((".", "!", "?", ":", ";")):
            parts.append(line)
        else:
            parts[-1] = prev + " " + line
    return "\n".join(parts)


def _render_bullet_list(text: str) -> str:
    result = []
    for ln in _lines_clean(text):
        clean = _NUMBERED_START.sub("", _BULLET_START.sub("", ln)).strip()
        if clean:
            result.append(f"- {clean}")
    return "\n".join(result)


def _render_numbered_list(text: str) -> str:
    result = []
    counter = 1
    for ln in _lines_clean(text):
        clean = _NUMBERED_START.sub("", _BULLET_START.sub("", ln)).strip()
        if clean:
            result.append(f"{counter}. {clean}")
            counter += 1
    return "\n".join(result)


def _render_mixed_list(text: str) -> str:
    result = []
    counter = 1
    for ln in _lines_clean(text):
        if _NUMBERED_START.match(ln):
            clean = _NUMBERED_START.sub("", ln).strip()
            result.append(f"{counter}. {clean}")
            counter += 1
        elif _BULLET_START.match(ln):
            result.append(f"- {_BULLET_START.sub('', ln).strip()}")
        else:
            result.append(f"- {ln}")
    return "\n".join(result)


def _render_callout(text: str, label: str = "NOTE") -> str:
    lines = _lines_clean(text)
    if not lines:
        return ""
    body = f"> [!{label}]\n> " + f"\n> ".join(lines)
    return body


def _render_marginal_note(text: str) -> str:
    return "\n".join(f"> {ln}" for ln in _lines_clean(text))


def _infer_list_kind(text: str) -> str:
    lines = _lines(text)
    num = sum(1 for ln in lines if _NUMBERED_START.match(ln.strip()))
    bul = sum(1 for ln in lines if _BULLET_START.match(ln.strip()))
    if num == len(lines):
        return "numbered"
    if num + bul == len(lines):
        return "mixed"
    return "bullet"


def _block_to_markdown(block: Block) -> str:
    text = (block.effective_content or "").strip()
    if not text:
        return ""
    bt = block.block_type
    if bt == BlockType.TITLE:
        return _render_title(text)
    if bt == BlockType.HEADING:
        return _render_heading(text, level=2)
    if bt == BlockType.BULLET_LIST:
        return _render_bullet_list(text) or _render_paragraph(text)
    if bt == BlockType.NUMBERED_LIST:
        kind = _infer_list_kind(text)
        if kind == "numbered":
            return _render_numbered_list(text)
        if kind == "mixed":
            return _render_mixed_list(text)
        return _render_bullet_list(text)
    if bt == BlockType.CALLOUT:
        vs = getattr(block, "visual_semantics", None)
        label = (vs.callout_label if vs and vs.callout_label else "NOTE")
        return _render_callout(text, label)
    if bt == BlockType.MARGINAL_NOTE:
        return _render_marginal_note(text)
    if bt == BlockType.URL_REFERENCE:
        url = text.strip()
        if url.startswith(("http://", "https://")):
            return f"[{url}]({url})"
        if url.startswith("www."):
            return f"[{url}](https://{url})"
        return f"<{url}>"
    if bt == BlockType.FORMULA:
        return f"$${text.strip()}$$"
    if bt in (BlockType.DIAGRAM, BlockType.TABLE):
        return ""
    # PARAGRAPH and everything else
    return _render_paragraph(text)


def reconstruct(blocks: list[Block]) -> str:
    sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)
    parts = [md for b in sorted_blocks if (md := _block_to_markdown(b))]
    return "\n\n".join(parts)
