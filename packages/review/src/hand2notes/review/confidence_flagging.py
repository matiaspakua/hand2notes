"""Confidence threshold flagging.

Sets block.review_flag=True for blocks below the configured threshold or with
no extracted content, so the review screen can highlight them.
"""

from hand2notes.core_models.models import Page


def flag_low_confidence_blocks(
    pages: list[Page],
    confidence_threshold: float = 0.65,
) -> int:
    """Flag blocks that need human review. Returns count of flagged blocks."""
    flagged = 0
    for page in pages:
        for block in page.blocks:
            needs_review = (
                block.confidence < confidence_threshold
                or block.content is None
            )
            block.review_flag = needs_review
            if needs_review:
                flagged += 1
    return flagged
