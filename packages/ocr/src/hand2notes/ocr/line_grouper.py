"""OCR line grouper: convert flat sorted text lines into structured blocks.

When Surya layout detection returns very few large blocks (e.g. one full-page
paragraph), this module takes the individual OCR line positions and re-builds
a richer block structure:

1. Group consecutive lines with small vertical gaps into paragraphs.
2. Detect list items (bullet / numbered) and keep them as separate items.
3. Detect short heading-like lines and mark them as HEADING / TITLE.
4. Rebuild a list[Block] that replaces the original coarse layout blocks.

This runs as a post-OCR step in the pipeline when the layout is too coarse.
"""

from __future__ import annotations

import re
from uuid import UUID

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox

# ── Grouping parameters ───────────────────────────────────────────────────────
_PARA_GAP_FACTOR = 1.4      # gap > factor × avg_height → new paragraph
_HEADING_GAP_FACTOR = 2.0   # gap > 2× avg_height before a line → likely heading
_HEADING_MAX_CHARS = 90
_HEADING_MIN_CHARS = 3

# ── Content patterns ──────────────────────────────────────────────────────────
_BULLET_RE = re.compile(r"^[\-\*\•·]\s+")
_NUMBERED_RE = re.compile(r"^\s*\d+[\.\)\-]\s+")
_SECTION_NUM_RE = re.compile(r"^\d+(\.\d+)?\s+[A-ZÁÉÍÓÚÑ]")
_NOISE_ONLY = re.compile(r"^[\s·\-–—\.]{0,3}$")


class _OcrLine:
    __slots__ = ("text", "confidence", "x1", "y1", "x2", "y2")

    def __init__(self, text: str, confidence: float, bbox: list[float]):
        self.text = text.strip()
        self.confidence = confidence
        b = bbox or [0, 0, 1, 1]
        self.x1, self.y1, self.x2, self.y2 = b[0], b[1], b[2], b[3]

    @property
    def height(self) -> float:
        return max(1.0, self.y2 - self.y1)

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2


# ── Public API ────────────────────────────────────────────────────────────────

def rebuild_blocks_from_lines(
    raw_lines: list,           # list of OcrLine-like objects with .text, .confidence, .bbox
    page_id: UUID,
    page_width: int,
    page_height: int,
    existing_blocks: list[Block] | None = None,
) -> list[Block]:
    """Re-derive block structure from sorted OCR lines.

    Args:
        raw_lines: OcrLine objects sorted top-to-bottom.
        page_id: UUID of the page these blocks belong to.
        existing_blocks: Original layout blocks; non-text blocks (diagrams, tables)
            are preserved and re-inserted at their reading-order positions.

    Returns:
        New list[Block] with proper structure inferred from line positions.
    """
    # Convert raw_lines to a normalised list
    lines = [_as_ocr_line(ln) for ln in raw_lines if _as_ocr_line(ln).text]
    lines = [ln for ln in lines if not _NOISE_ONLY.match(ln.text)]

    if not lines:
        return existing_blocks or []

    avg_h = _avg_height(lines)
    groups = _group_lines(lines, avg_h)
    blocks = [_group_to_block(g, i, page_id, avg_h, page_height)
              for i, g in enumerate(groups)]

    # Preserve non-text blocks (diagrams, tables) from the original layout
    if existing_blocks:
        preserved = [b for b in existing_blocks
                     if b.block_type in (BlockType.DIAGRAM, BlockType.TABLE,
                                         BlockType.URL_REFERENCE, BlockType.FORMULA)]
        if preserved:
            blocks.extend(preserved)
            blocks.sort(key=lambda b: b.bbox.y)
            for i, b in enumerate(blocks):
                b.reading_order = i

    return blocks


# ── Line grouping ─────────────────────────────────────────────────────────────

def _group_lines(lines: list[_OcrLine], avg_h: float) -> list[list[_OcrLine]]:
    """Group consecutive lines by vertical proximity."""
    groups: list[list[_OcrLine]] = []

    # Special case: if the very first line looks like a page title, isolate it.
    start_idx = 0
    if lines and _looks_like_heading_line(lines[0].text, []) and len(lines) > 1:
        groups.append([lines[0]])
        start_idx = 1

    if start_idx >= len(lines):
        return groups

    current: list[_OcrLine] = [lines[start_idx]]

    for ln in lines[start_idx + 1:]:
        prev = current[-1]
        gap = ln.y1 - prev.y2

        # Large gap → new block
        if gap > _PARA_GAP_FACTOR * avg_h:
            groups.append(current)
            current = [ln]
            continue

        # List items are always kept as separate single-line blocks
        if _is_list_line(ln.text):
            groups.append(current)
            current = [ln]
            continue

        # Heading-like line following any positive gap → new block
        if gap > 0.5 * avg_h and _looks_like_heading_line(ln.text, current):
            groups.append(current)
            current = [ln]
            continue

        # Accumulate into current paragraph (max 5 lines to avoid over-merging)
        if len(current) >= 5:
            groups.append(current)
            current = [ln]
            continue

        current.append(ln)

    if current:
        groups.append(current)
    return groups


def _group_to_block(
    group: list[_OcrLine],
    order: int,
    page_id: UUID,
    avg_h: float,
    page_height: int,
) -> Block:
    """Convert a group of consecutive lines into one Block."""
    text = "\n".join(ln.text for ln in group)
    x1 = min(ln.x1 for ln in group)
    y1 = min(ln.y1 for ln in group)
    x2 = max(ln.x2 for ln in group)
    y2 = max(ln.y2 for ln in group)
    conf = sum(ln.confidence for ln in group) / len(group)

    block_type = _classify_group(group, y1, page_height, avg_h)

    return Block(
        page_id=page_id,
        block_type=block_type,
        reading_order=order,
        bbox=BoundingBox(
            x=max(0, int(x1)),
            y=max(0, int(y1)),
            width=max(1, int(x2 - x1)),
            height=max(1, int(y2 - y1)),
        ),
        confidence=conf,
        content=text,
    )


def _classify_group(
    group: list[_OcrLine],
    y_top: float,
    page_height: int,
    avg_h: float,
) -> BlockType:
    first_text = group[0].text.strip()

    # Single line with bullet/number marker
    if len(group) == 1:
        if _BULLET_RE.match(first_text):
            return BlockType.BULLET_LIST
        if _NUMBERED_RE.match(first_text):
            return BlockType.NUMBERED_LIST

    # Multi-line where every line is a bullet/number
    if all(_BULLET_RE.match(ln.text) for ln in group):
        return BlockType.BULLET_LIST
    if all(_NUMBERED_RE.match(ln.text) for ln in group):
        return BlockType.NUMBERED_LIST

    # Section number heading: "2 Heading text"
    if len(group) == 1 and _SECTION_NUM_RE.match(first_text):
        return BlockType.HEADING

    # Heading detection: short, capitalised, single line
    if _is_heading_group(group, y_top, page_height, avg_h):
        is_near_top = y_top < page_height * 0.20
        words = first_text.split()
        cap_ratio = sum(1 for w in words if w and w[0].isupper()) / max(len(words), 1)
        if is_near_top and len(first_text) < 60 and cap_ratio >= 0.6:
            return BlockType.TITLE
        return BlockType.HEADING

    return BlockType.PARAGRAPH


def _is_heading_group(
    group: list[_OcrLine],
    y_top: float,
    page_height: int,
    avg_h: float,
) -> bool:
    if len(group) != 1:
        return False
    text = group[0].text.strip()
    if not (_HEADING_MIN_CHARS <= len(text) <= _HEADING_MAX_CHARS):
        return False
    words = text.split()
    if not words:
        return False
    if words[0][0].islower() and len(text) < 15:
        return False  # very short lowercase → probably body fragment
    cap_ratio = sum(1 for w in words if w and w[0].isupper()) / len(words)
    return cap_ratio >= 0.55 and not text.endswith((",", ";"))


def _looks_like_heading_line(text: str, preceding: list[_OcrLine]) -> bool:
    """True if this line introduces a new section after the preceding group."""
    t = text.strip()
    if not t or len(t) > _HEADING_MAX_CHARS:
        return False
    if _SECTION_NUM_RE.match(t):
        return True
    words = t.split()
    if not words:
        return False
    cap_ratio = sum(1 for w in words if w and w[0].isupper()) / len(words)
    return cap_ratio >= 0.6 and not t.endswith((",", ";"))


def _is_list_line(text: str) -> bool:
    t = text.strip()
    return bool(_BULLET_RE.match(t) or _NUMBERED_RE.match(t))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _avg_height(lines: list[_OcrLine]) -> float:
    hs = [ln.height for ln in lines if ln.height > 2]
    return sum(hs) / len(hs) if hs else 20.0


def _as_ocr_line(obj) -> _OcrLine:
    """Normalise a raw OcrLine-like object."""
    text = getattr(obj, "text", "") or ""
    conf = getattr(obj, "confidence", 0.5) or 0.5
    bbox = getattr(obj, "bbox", None) or [0, 0, 1, 1]
    return _OcrLine(text=text, confidence=conf, bbox=list(bbox))
