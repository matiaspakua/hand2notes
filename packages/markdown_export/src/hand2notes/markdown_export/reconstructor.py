"""Structure reconstructor: maps BlockType → Markdown elements.

Preserves reading order. Uses effective_content (corrected_content > content).
Handles multi-line block content (Surya OCR produces newline-separated lines).
"""

import re

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block

# Leading digit(s) followed by . or ) or - → numbered item
_NUMBERED_ITEM_RE = re.compile(r"^\s*(\d+)\s*[\.\)\-]\s+")


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _render_bullet_lines(text: str) -> str:
    items = _lines(text)
    if not items:
        return ""
    result = []
    for item in items:
        clean = re.sub(r"^[\-\*\•]\s*", "", item).strip()
        clean = _NUMBERED_ITEM_RE.sub("", clean).strip()
        if clean:
            result.append(f"- {clean}")
    return "\n".join(result)


def _render_numbered_lines(text: str) -> str:
    items = _lines(text)
    if not items:
        return ""
    result = []
    for i, item in enumerate(items, 1):
        clean = re.sub(r"^[\-\*\•]\s*", "", item).strip()
        clean = _NUMBERED_ITEM_RE.sub("", clean).strip()
        if clean:
            result.append(f"{i}. {clean}")
    return "\n".join(result)


def _strip_leading_number(text: str) -> str:
    """Remove leading '2 ' / '2.' / '2)' style prefixes from a heading line."""
    return re.sub(r"^\s*\d+[\s\.\-\)]+\s*", "", text).strip() or text


def _infer_block_type_from_content(text: str, declared: BlockType) -> BlockType:
    """Refine declared block type from OCR content heuristics."""
    if declared not in (BlockType.PARAGRAPH, BlockType.BULLET_LIST, BlockType.NUMBERED_LIST):
        return declared
    first = (_lines(text) or [""])[0]
    if _NUMBERED_ITEM_RE.match(first):
        return BlockType.NUMBERED_LIST
    if re.match(r"^[\-\*\•]\s+", first):
        return BlockType.BULLET_LIST
    return declared


def _render_list_block(text: str, block_type: BlockType) -> str:
    """Render a block whose lines may be a mix of numbered and unnumbered items.

    If ALL lines that start with a digit are sequentially numbered (1, 2, 3 …),
    render as a Markdown numbered list.  Otherwise render as bullet list.
    """
    raw_lines = _lines(text)
    if not raw_lines:
        return ""

    # Count how many lines look like numbered items
    numbered = [_NUMBERED_ITEM_RE.match(ln) for ln in raw_lines]
    numbered_count = sum(1 for m in numbered if m)

    if block_type == BlockType.NUMBERED_LIST or numbered_count == len(raw_lines):
        return _render_numbered_lines(text)
    elif block_type == BlockType.BULLET_LIST:
        return _render_bullet_lines(text)
    else:
        # Mixed: render each line individually with its natural marker
        parts = []
        counter = 1
        for ln, m in zip(raw_lines, numbered):
            if m:
                clean = _NUMBERED_ITEM_RE.sub("", ln).strip()
                parts.append(f"{counter}. {clean}")
                counter += 1
            else:
                clean = re.sub(r"^[\-\*\•]\s*", "", ln).strip()
                parts.append(f"- {clean}" if clean else f"- {ln}")
        return "\n".join(parts)


def _block_to_markdown(block: Block) -> str:
    text = (block.effective_content or "").strip()
    if not text:
        return ""

    block_type = _infer_block_type_from_content(text, block.block_type)

    match block_type:
        case BlockType.TITLE:
            return f"# {_strip_leading_number(_lines(text)[0])}"

        case BlockType.HEADING:
            return f"## {_strip_leading_number(_lines(text)[0])}"

        case BlockType.BULLET_LIST | BlockType.NUMBERED_LIST:
            return _render_list_block(text, block_type)

        case BlockType.CALLOUT:
            first = _lines(text)[0] if _lines(text) else text
            return f"> [!NOTE]\n> {first}"

        case BlockType.MARGINAL_NOTE:
            return "\n".join(f"> {ln}" for ln in _lines(text))

        case BlockType.URL_REFERENCE:
            url = text.strip()
            return f"[{url}]({url})"

        case BlockType.FORMULA:
            return f"$${text}$$"

        case BlockType.DIAGRAM | BlockType.TABLE:
            if block.crop_path:
                return f"![{block.block_type.value}]({block.crop_path})"
            return f"<!-- {block.block_type.value} block -->"

        case _:
            # PARAGRAPH: join lines with single newlines inside the paragraph
            return "\n".join(_lines(text))


def reconstruct(blocks: list[Block]) -> str:
    """Convert an ordered list of blocks to a single Markdown string."""
    sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)
    parts = []
    for block in sorted_blocks:
        md = _block_to_markdown(block)
        if md:
            parts.append(md)
    return "\n\n".join(parts)
