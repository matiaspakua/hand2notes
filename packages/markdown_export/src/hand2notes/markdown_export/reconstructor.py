"""Structure reconstructor: maps BlockType → Markdown elements."""

from __future__ import annotations

import re

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block

_BULLET_START = re.compile(r"^[\-\*\•·]\s*")
_NUMBERED_START = re.compile(r"^\s*(\d+)\s*[\.\)\-]\s*")
# Arrow normalization intentionally disabled — VLM output already uses `-->`
# notation which must be preserved verbatim in the exported Markdown.
_ARROW_NORM: list = []
# Pipe-only lines (`|`) are valid structural connectors (e.g. flowchart arrows),
# not noise. Only filter truly empty or pure punctuation-only short strings.
_NOISE_RE = re.compile(r"^[·.·•\-–—=+/\\]{1,3}$")


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _clean_line(text: str) -> str:
    t = text
    for pattern, repl in _ARROW_NORM:
        t = pattern.sub(repl, t)
    return t.strip()


def _is_noise(text: str) -> bool:
    stripped = text.strip()
    # Single `|` is a valid structural connector (flowchart/arrow notation)
    if stripped == "|":
        return False
    return bool(_NOISE_RE.match(stripped)) or len(stripped) < 2


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


_STRUCTURAL_MARKERS = re.compile(r"--+>|<--+|\|-+>|\|$", re.MULTILINE)


def _has_structure(text: str) -> bool:
    """True when the text contains arrow/connector markers that must not be reflowed."""
    return bool(_STRUCTURAL_MARKERS.search(text))


def _render_paragraph(text: str) -> str:
    # Pre-formatted multi-line content (arrows, connectors): preserve as-is
    if _has_structure(text):
        raw_lines = text.splitlines()
        kept = [ln for ln in raw_lines if not _is_noise(ln)]
        return "\n".join(kept) if kept else ""

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


_N_DOT_SPACE = re.compile(r"^\d+\s+\.\s+")
_N_PAREN = re.compile(r"^\d+\)")


def _split_list_trailing(text: str) -> tuple[str, str]:
    """Split a list block into (list_items_text, trailing_structural_text).

    Trailing structural lines (connectors, spatial layout) that follow the last
    list item are returned separately so they can be rendered verbatim.
    """
    raw_lines = text.splitlines()
    last_list_idx = -1
    for i, ln in enumerate(raw_lines):
        stripped = ln.strip()
        if (_NUMBERED_START.match(stripped) or _BULLET_START.match(stripped)
                or _N_DOT_SPACE.match(stripped) or _N_PAREN.match(stripped)):
            last_list_idx = i
    if last_list_idx < 0 or last_list_idx == len(raw_lines) - 1:
        return text, ""
    list_part = "\n".join(raw_lines[: last_list_idx + 1])
    trail_part = "\n".join(raw_lines[last_list_idx + 1 :])
    return list_part, trail_part


def _render_numbered_list(text: str) -> str:
    list_part, trail_part = _split_list_trailing(text)
    raw = _lines_clean(list_part)
    if not raw:
        return trail_part if trail_part.strip() else ""
    # If lines already carry "N . text" or "N) text" notation, preserve verbatim
    if all(_N_DOT_SPACE.match(ln) or _N_PAREN.match(ln) for ln in raw):
        result = "\n".join(raw)
    else:
        items = []
        counter = 1
        for ln in raw:
            clean = _NUMBERED_START.sub("", _BULLET_START.sub("", ln)).strip()
            if clean:
                items.append(f"{counter}. {clean}")
                counter += 1
        result = "\n".join(items)
    if trail_part.strip():
        # Remove leading blank lines from trailing; join directly (no blank separator)
        trail_stripped = trail_part.lstrip("\n")
        result = result + "\n" + trail_stripped
    return result


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
    # Exclude trailing structural/connector lines (spatial layout blocks appended to
    # lists by the parser) when classifying — they are not list items.
    list_lines = [
        ln for ln in lines
        if _NUMBERED_START.match(ln.strip())
        or _BULLET_START.match(ln.strip())
    ]
    if not list_lines:
        return "bullet"
    num = sum(1 for ln in list_lines if _NUMBERED_START.match(ln.strip()))
    bul = sum(1 for ln in list_lines if _BULLET_START.match(ln.strip()))
    if num == len(list_lines):
        return "numbered"
    if num + bul == len(list_lines):
        return "mixed"
    return "bullet"


def _block_to_markdown(block: Block) -> str:
    raw = block.effective_content or ""
    # For pre-formatted content (contains structural markers), preserve indentation.
    # Other block types go through their respective formatters which handle stripping.
    text = raw if _has_structure(raw) else raw.strip()
    if not text or not text.strip():
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
