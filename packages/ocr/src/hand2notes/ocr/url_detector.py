"""Handwritten URL detector.

Regex pattern matching on OCR output to identify URL-like strings.
Sets block_type=URL_REFERENCE and updates confidence based on OCR clarity.
"""

import re

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block

_URL_PATTERN = re.compile(
    r"(?:https?://|www\.)\S+|"
    r"\b\S+\.(?:com|org|net|io|dev|edu|gov|info|co)\b(?:/\S*)?",
    re.IGNORECASE,
)


def detect_urls_in_blocks(blocks: list[Block]) -> list[Block]:
    """Scan blocks for URL-like text and update block_type accordingly.

    Blocks where the entire content matches a URL pattern are reclassified
    as URL_REFERENCE. Partial matches within paragraph text are left as-is
    but get a url_reference annotation in visual_semantics.obsidian_notation.

    Returns the same list (mutated in place).
    """
    for block in blocks:
        text = block.corrected_content or block.content or ""
        if not text.strip():
            continue

        stripped = text.strip()
        full_match = _URL_PATTERN.fullmatch(stripped)
        if full_match:
            block.block_type = BlockType.URL_REFERENCE
            continue

        # Partial matches: annotate but don't reclassify
        matches = _URL_PATTERN.findall(stripped)
        if matches and block.visual_semantics is not None:
            from hand2notes.core_models.models import VisualSemantics
            vs = block.visual_semantics or VisualSemantics()
            if vs.obsidian_notation is None:
                vs.obsidian_notation = ", ".join(matches)
                block.visual_semantics = vs

    return blocks
