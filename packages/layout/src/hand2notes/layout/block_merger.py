"""Spatial block merger: collapse Surya's many tiny regions into logical units.

Surya layout detection produces fine-grained text regions — often 30-50 blocks
per page where 8-15 logical paragraphs/sections exist.  This module merges them
into coherent units so the markdown renderer can produce clean output.

Merge pass 1 — inline merge:
  Blocks whose vertical centres overlap within the same horizontal band are
  on the same "text line".  Merge them left-to-right into a single block.

Merge pass 2 — paragraph merge:
  Consecutive merged lines whose vertical gap is ≤ LINE_GAP_FACTOR × avg_height
  belong to the same paragraph.  Merge them top-to-bottom.

The merged blocks inherit the block_type of the dominant (largest) constituent.
Content is concatenated with the appropriate separator.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Sequence

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox

# Vertical-overlap fraction threshold for "same line"
_SAME_LINE_Y_OVERLAP = 0.4
# Gap factor: if gap_between_lines < factor * avg_height → same paragraph
_INLINE_GAP_FACTOR = 0.8   # horizontal gap within a line (chars on same row)
_PARA_GAP_FACTOR = 1.1     # vertical gap factor for paragraph continuation (conservative)
_MAX_PARA_LINES = 5        # don't merge groups that would exceed this many text lines
# Block types that should NEVER be merged into other blocks
_ISOLATED_TYPES: frozenset[BlockType] = frozenset({
    BlockType.TABLE,
    BlockType.DIAGRAM,
    BlockType.URL_REFERENCE,
    BlockType.FORMULA,
})
# Block types that are ONLY merged with same-type neighbours
_SAME_TYPE_ONLY: frozenset[BlockType] = frozenset({
    BlockType.BULLET_LIST,
    BlockType.NUMBERED_LIST,
})


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def merge_page_blocks(
    blocks: Sequence[Block],
    page_width: int,
    page_height: int,
) -> list[Block]:
    """Return a de-fragmented list of blocks for one page.

    The returned blocks are new copies; originals are not mutated.
    """
    if not blocks:
        return []

    # Split isolated types out (they go through unchanged)
    isolated = [b for b in blocks if b.block_type in _ISOLATED_TYPES]
    mergeable = [b for b in blocks if b.block_type not in _ISOLATED_TYPES]

    if not mergeable:
        return list(blocks)

    avg_height = _avg_height(mergeable)

    # Pass 1: merge inline (same row, left to right)
    rows = _group_into_rows(mergeable, avg_height)
    inline_merged = [_merge_row(row) for row in rows]

    # Pass 2: merge rows into paragraphs
    paragraphs = _merge_rows_into_paragraphs(inline_merged, avg_height)

    # Re-combine with isolated blocks, sorted by reading_order
    result = paragraphs + isolated
    result.sort(key=lambda b: b.reading_order)

    # Re-assign sequential reading orders
    for i, b in enumerate(result):
        b.reading_order = i

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Pass 1 — group blocks that share the same horizontal text row
# ─────────────────────────────────────────────────────────────────────────────

def _group_into_rows(blocks: list[Block], avg_height: float) -> list[list[Block]]:
    """Cluster blocks into rows based on vertical centre overlap."""
    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox.y, b.bbox.x))
    rows: list[list[Block]] = []
    current_row: list[Block] = []

    for block in sorted_blocks:
        if not current_row:
            current_row.append(block)
            continue

        # y_overlap: is this block's centre within the row's vertical band?
        row_top = min(b.bbox.y for b in current_row)
        row_bot = max(b.bbox.y + b.bbox.height for b in current_row)
        row_h = row_bot - row_top or avg_height

        overlap = (min(block.bbox.y + block.bbox.height, row_bot) -
                   max(block.bbox.y, row_top)) / row_h

        if overlap >= _SAME_LINE_Y_OVERLAP:
            current_row.append(block)
        else:
            rows.append(current_row)
            current_row = [block]

    if current_row:
        rows.append(current_row)
    return rows


def _merge_row(row: list[Block]) -> Block:
    """Merge a row of left-to-right blocks into a single block."""
    if len(row) == 1:
        return copy.copy(row[0])

    row_sorted = sorted(row, key=lambda b: b.bbox.x)
    dominant = max(row_sorted, key=lambda b: b.bbox.width * b.bbox.height)
    merged = copy.copy(dominant)

    # Bounding box encompassing all blocks
    x1 = min(b.bbox.x for b in row_sorted)
    y1 = min(b.bbox.y for b in row_sorted)
    x2 = max(b.bbox.x + b.bbox.width for b in row_sorted)
    y2 = max(b.bbox.y + b.bbox.height for b in row_sorted)
    merged.bbox = BoundingBox(x=x1, y=y1, width=max(1, x2 - x1), height=max(1, y2 - y1))

    # Concatenate text left-to-right, separated by space
    parts = []
    for b in row_sorted:
        txt = (b.auto_corrected_content or b.content or "").strip()
        if txt:
            parts.append(txt)
    merged.content = " ".join(parts) if parts else merged.content
    merged.auto_corrected_content = None  # reset; content is now the merged value

    # Confidence = mean
    confs = [b.confidence for b in row_sorted if b.confidence]
    merged.confidence = sum(confs) / len(confs) if confs else merged.confidence

    # Reading order = min of constituents
    merged.reading_order = min(b.reading_order for b in row_sorted)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Pass 2 — merge consecutive rows that belong to the same paragraph
# ─────────────────────────────────────────────────────────────────────────────

def _merge_rows_into_paragraphs(rows: list[Block], avg_height: float) -> list[Block]:
    """Join rows that have small vertical gaps into paragraph blocks."""
    if not rows:
        return []

    rows_sorted = sorted(rows, key=lambda b: b.bbox.y)
    groups: list[list[Block]] = []
    current: list[Block] = [rows_sorted[0]]

    for block in rows_sorted[1:]:
        prev = current[-1]
        gap = block.bbox.y - (prev.bbox.y + prev.bbox.height)
        threshold = _PARA_GAP_FACTOR * avg_height

        # Count how many lines current group already has
        current_lines = sum(
            len([ln for ln in (b.content or "").splitlines() if ln.strip()])
            for b in current
        )

        can_merge = (
            gap <= threshold
            and current_lines < _MAX_PARA_LINES
            and not _is_list_block(block)
            and not _is_list_block(prev)
            and block.block_type not in _SAME_TYPE_ONLY
            and prev.block_type not in _SAME_TYPE_ONLY
            and not _looks_like_heading(prev)  # headings start a new group
        )

        if can_merge:
            current.append(block)
        else:
            groups.append(current)
            current = [block]
    groups.append(current)

    result = []
    for group in groups:
        result.append(_merge_paragraph_group(group))
    return result


def _merge_paragraph_group(group: list[Block]) -> Block:
    """Merge a vertical list of row-blocks into a single paragraph block."""
    if len(group) == 1:
        return group[0]

    # Dominant block = one with most text
    dominant = max(group, key=lambda b: len(b.content or ""))
    merged = copy.copy(dominant)

    # Encompassing bbox
    x1 = min(b.bbox.x for b in group)
    y1 = min(b.bbox.y for b in group)
    x2 = max(b.bbox.x + b.bbox.width for b in group)
    y2 = max(b.bbox.y + b.bbox.height for b in group)
    merged.bbox = BoundingBox(x=x1, y=y1, width=max(1, x2 - x1), height=max(1, y2 - y1))

    # Concatenate lines (top-to-bottom)
    lines = []
    for b in sorted(group, key=lambda b: b.bbox.y):
        txt = (b.auto_corrected_content or b.content or "").strip()
        if txt:
            lines.append(txt)
    merged.content = "\n".join(lines) if lines else merged.content
    merged.auto_corrected_content = None

    confs = [b.confidence for b in group if b.confidence]
    merged.confidence = sum(confs) / len(confs) if confs else merged.confidence
    merged.reading_order = min(b.reading_order for b in group)

    # If any constituent was flagged for review, propagate the flag
    merged.review_flag = any(b.review_flag for b in group)

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _avg_height(blocks: list[Block]) -> float:
    heights = [b.bbox.height for b in blocks if b.bbox.height > 0]
    return sum(heights) / len(heights) if heights else 20.0


def _centre_y(blocks: list[Block]) -> float:
    ys = [b.bbox.y + b.bbox.height / 2 for b in blocks]
    return sum(ys) / len(ys)


_SHORT_SINGLE_RE = re.compile(r"^.{3,80}$", re.DOTALL)
_SECTION_NUM_BLOCK = re.compile(r"^\d+(\.\d+)?\s+[A-ZÁÉÍÓÚÑ]")


def _looks_like_heading(block: Block) -> bool:
    """True when a block's content suggests it is a section heading."""
    text = (block.content or "").strip()
    if block.block_type in (BlockType.HEADING, BlockType.TITLE):
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) != 1:
        return False
    line = lines[0]
    if len(line) > 80:
        return False
    if _SECTION_NUM_BLOCK.match(line):
        return True
    words = line.split()
    if not words:
        return False
    cap_count = sum(1 for w in words if w and w[0].isupper())
    return cap_count / len(words) >= 0.7 and not line.endswith((",", ";"))


def _is_list_block(block: Block) -> bool:
    import re
    text = (block.content or "").strip()
    if block.block_type in (BlockType.BULLET_LIST, BlockType.NUMBERED_LIST):
        return True
    if re.match(r"^[\-\*\•]\s+", text):
        return True
    if re.match(r"^\s*\d+[\.\)\-]\s+", text):
        return True
    return False
