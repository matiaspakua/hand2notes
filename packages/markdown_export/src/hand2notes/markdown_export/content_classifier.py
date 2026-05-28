"""Content-aware block classifier.

Surya's layout model sometimes mis-labels blocks (e.g. calls a section
heading a PARAGRAPH).  This module re-classifies blocks using:

  - Text content analysis  (length, patterns, capitalisation)
  - Spatial context        (block height relative to neighbours, vertical position)
  - Visual semantics       (boxed, circled, highlighted)

Re-classification is non-destructive: original `block_type` is preserved;
the returned mapping is {block_id → BlockType}.
"""

from __future__ import annotations

import re
from uuid import UUID

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block

# ── Heading detection ──────────────────────────────────────────────────────────

# Patterns that strongly suggest a heading
_SECTION_END_PATTERN = re.compile(
    r"[:：]\s*$"           # ends with colon
)
_HEADING_INTRO_PATTERN = re.compile(
    r"^(#+\s+)",           # already marked as heading
)
# Patterns that suggest this is NOT a heading (it's body text)
# Note: period is intentionally excluded — Spanish headings often end with "."
_NOT_HEADING_PATTERNS = [
    re.compile(r",\s*$"),                 # ends with comma
    re.compile(r"\band\s+\w{4,}", re.I), # "and something" — mid-sentence connector
    re.compile(r"\s{3,}"),               # lots of whitespace → looks like a data row
]

# Section-number prefix pattern: "2 Heading text" or "2.1 Heading"
_SECTION_NUM_RE = re.compile(r"^\d+(\.\d+)?\s+[A-ZÁÉÍÓÚÑ]")
# Max character length for heading detection
_HEADING_MAX_LEN = 80
_HEADING_MIN_LEN = 3

# Patterns indicating a list item
_BULLET_START = re.compile(r"^[\-\*\•·]\s+")
_NUMBERED_START = re.compile(r"^\s*\d+[\.\)\-]\s+")

# Patterns for inline emphasis markers
_ARROW_PATTERN = re.compile(r"→|->|←|-<|↑|↓")
_ALL_CAPS_WORD = re.compile(r"\b[A-ZÁÉÍÓÚÑ]{3,}\b")


def classify_blocks(
    blocks: list[Block],
    page_height: int = 1000,
    page_width: int = 800,
) -> dict[UUID, BlockType]:
    """Return a mapping of block_id → inferred BlockType.

    Only IDs whose type changes are included; absent IDs keep their declared type.
    """
    if not blocks:
        return {}

    overrides: dict[UUID, BlockType] = {}
    avg_h = _avg_block_height(blocks)
    sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)

    # Spatial context: top-N % of page is more likely to have titles
    page_top_threshold = page_height * 0.15

    for i, block in enumerate(sorted_blocks):
        if block.block_type in (BlockType.DIAGRAM, BlockType.TABLE,
                                 BlockType.URL_REFERENCE, BlockType.FORMULA):
            continue  # never reclassify structural blocks

        text = (block.auto_corrected_content or block.content or "").strip()
        if not text:
            continue

        inferred = _infer_type(
            block=block,
            text=text,
            avg_height=avg_h,
            is_near_top=block.bbox.y < page_top_threshold,
            neighbours=[sorted_blocks[i - 1] if i > 0 else None,
                        sorted_blocks[i + 1] if i < len(sorted_blocks) - 1 else None],
            is_first_block=(i == 0),
        )

        if inferred != block.block_type:
            overrides[block.id] = inferred

    return overrides


def apply_overrides(blocks: list[Block], overrides: dict[UUID, BlockType]) -> None:
    """Mutate block.block_type in-place for all blocks in the overrides map."""
    for block in blocks:
        if block.id in overrides:
            block.block_type = overrides[block.id]


def _infer_type(
    block: Block,
    text: str,
    avg_height: float,
    is_near_top: bool,
    neighbours: list[Block | None],
    is_first_block: bool = False,
) -> BlockType:
    declared = block.block_type
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first_line = lines[0] if lines else text

    # ── Section-number prefix: "2 Heading" or "2.1 Heading" ─────────────────
    # Must check BEFORE list detection so "2 Estrategia" → HEADING not NUMBERED_LIST
    if _SECTION_NUM_RE.match(first_line) and len(lines) == 1 and len(first_line) <= _HEADING_MAX_LEN:
        return BlockType.HEADING

    # ── Already a list type? respect it ──────────────────────────────────────
    if declared in (BlockType.BULLET_LIST, BlockType.NUMBERED_LIST):
        return declared

    # ── List detection from content ──────────────────────────────────────────
    if _BULLET_START.match(first_line):
        return BlockType.BULLET_LIST
    if _NUMBERED_START.match(first_line):
        return BlockType.NUMBERED_LIST

    # ── All lines start with a bullet/number → list ───────────────────────────
    if len(lines) > 1:
        if all(_BULLET_START.match(ln) for ln in lines):
            return BlockType.BULLET_LIST
        if all(_NUMBERED_START.match(ln) for ln in lines):
            return BlockType.NUMBERED_LIST

    # ── Heading detection ─────────────────────────────────────────────────────
    char_len = len(first_line)

    is_short = _HEADING_MIN_LEN <= char_len <= _HEADING_MAX_LEN
    is_single_line = len(lines) == 1
    has_caps = first_line[0].isupper() if first_line else False
    is_visually_large = block.bbox.height > avg_height * 1.25
    ends_with_colon = bool(_SECTION_END_PATTERN.search(first_line))
    all_words_cap = _is_title_case_or_caps(first_line)
    has_all_caps_word = bool(_ALL_CAPS_WORD.search(first_line))

    # Body-text disqualifiers
    is_body = any(p.search(first_line) for p in _NOT_HEADING_PATTERNS)

    heading_score = sum([
        is_short,
        is_single_line,
        has_caps,
        is_visually_large,
        ends_with_colon,
        all_words_cap,
        has_all_caps_word,
        is_near_top,
        is_first_block,  # first block on page is very likely a title/heading
        not is_body,
    ])

    if declared in (BlockType.HEADING, BlockType.TITLE):
        # Downgrade single lowercase words — likely OCR fragment mis-labelled as heading
        if char_len < 15 and first_line[0].islower() and " " not in first_line:
            return BlockType.PARAGRAPH
        if is_near_top and char_len < 60:
            return BlockType.TITLE
        return declared

    if declared == BlockType.PARAGRAPH:
        if heading_score >= 5 and is_short and is_single_line:
            if (is_near_top or is_first_block) and char_len < 60:
                return BlockType.TITLE
            return BlockType.HEADING

        vs = getattr(block, "visual_semantics", None)
        if vs and (getattr(vs, "is_boxed", False) or getattr(vs, "is_circled", False)):
            return BlockType.CALLOUT

    return declared


# ── Helpers ────────────────────────────────────────────────────────────────────

def _avg_block_height(blocks: list[Block]) -> float:
    heights = [b.bbox.height for b in blocks
               if b.block_type not in (BlockType.DIAGRAM, BlockType.TABLE)]
    return sum(heights) / len(heights) if heights else 20.0


def _is_title_case_or_caps(text: str) -> bool:
    words = text.split()
    if not words:
        return False
    significant = [w for w in words if len(w) > 2]
    if not significant:
        return True
    cap_count = sum(1 for w in significant if w[0].isupper())
    return cap_count / len(significant) >= 0.6
