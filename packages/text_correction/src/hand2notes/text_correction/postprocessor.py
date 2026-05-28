"""Block-level post-processor: applies spell correction to all text blocks on a page.

Only text-bearing block types are corrected; diagrams, tables with structured
data, and URL references are left untouched.
"""

from __future__ import annotations

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, Page

from .corrector import CorrectionResult, SpellCorrector, get_corrector

# Block types that carry unstructured OCR text and benefit from spell correction.
_CORRECTABLE_TYPES: frozenset[BlockType] = frozenset({
    BlockType.PARAGRAPH,
    BlockType.HEADING,
    BlockType.TITLE,
    BlockType.BULLET_LIST,
    BlockType.NUMBERED_LIST,
    BlockType.MARGINAL_NOTE,
    BlockType.CALLOUT,
})


def correct_page(
    page: Page,
    languages: list[str] | None = None,
    corrector: SpellCorrector | None = None,
) -> dict[str, int]:
    """Apply spell correction to all correctable blocks on *page*.

    Sets ``block.auto_corrected_content`` for each block that was altered.
    Returns metrics: {blocks_checked, blocks_corrected, words_corrected}.
    """
    langs = languages or ["es", "en"]
    checker = corrector or get_corrector(langs)

    blocks_checked = 0
    blocks_corrected = 0
    words_corrected = 0

    for block in page.blocks:
        if block.block_type not in _CORRECTABLE_TYPES:
            continue
        raw = block.content
        if not raw or not raw.strip():
            continue

        blocks_checked += 1
        result = checker.correct_text(raw)
        if result.corrections_applied > 0:
            block.auto_corrected_content = result.corrected
            blocks_corrected += 1
            words_corrected += result.corrections_applied

    return {
        "blocks_checked": blocks_checked,
        "blocks_corrected": blocks_corrected,
        "words_corrected": words_corrected,
    }
