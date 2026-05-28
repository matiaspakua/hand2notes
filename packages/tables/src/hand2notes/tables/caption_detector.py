"""Table caption detection.

Reads the nearest text block above the table region and assigns it as caption.
"""

from hand2notes.core_models.blocks import TableBlock
from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block


def detect_caption(table_block: TableBlock, all_blocks: list[Block]) -> str | None:
    """Find the closest text block above the table and return its content as caption.

    Returns None if no suitable candidate is found.
    """
    table_top = table_block.bbox.y
    table_left = table_block.bbox.x
    table_right = table_block.bbox.x + table_block.bbox.width

    candidates: list[tuple[int, Block]] = []
    for block in all_blocks:
        if block.id == table_block.id:
            continue
        if block.block_type not in (BlockType.PARAGRAPH, BlockType.HEADING, BlockType.TITLE):
            continue
        block_bottom = block.bbox.y + block.bbox.height
        # Must be above the table
        if block_bottom > table_top:
            continue
        # Must horizontally overlap
        block_right = block.bbox.x + block.bbox.width
        overlap = min(block_right, table_right) - max(block.bbox.x, table_left)
        if overlap <= 0:
            continue
        gap = table_top - block_bottom
        candidates.append((gap, block))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    closest = candidates[0][1]
    content = closest.corrected_content or closest.content
    return content.strip() if content else None
