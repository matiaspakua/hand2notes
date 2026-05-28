"""Block correction service.

Writes corrected_content to a block, clears review_flag, and updates the
parent page's review_status. DB persistence is optional (wired in Phase 5).
"""

from uuid import UUID

from hand2notes.core_models.enums import ReviewStatus
from hand2notes.core_models.models import Block, Page


def apply_correction(
    page: Page,
    block_id: UUID,
    corrected_content: str,
    *,
    review_flag: bool = False,
) -> Block | None:
    """Apply a text correction to a block and update page review status.

    Returns the updated Block or None if not found.
    """
    target: Block | None = None
    for block in page.blocks:
        if block.id == block_id:
            target = block
            break

    if target is None:
        return None

    target.corrected_content = corrected_content
    target.review_flag = review_flag

    # Recompute page review status
    all_flagged = [b for b in page.blocks if b.review_flag]
    if all_flagged:
        page.review_status = ReviewStatus.FLAGGED
    else:
        page.review_status = ReviewStatus.APPROVED

    return target
