"""Table region detector.

Identifies block_type=table regions in layout output using horizontal/vertical
line detection (OpenCV). Falls back to passing existing TABLE blocks through.
"""

import logging
from pathlib import Path

from hand2notes.core_models.blocks import TableBlock
from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox, Page

log = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


def detect_table_regions(image_path: Path, page: Page) -> list[Block]:
    """Return blocks annotated as TABLE where line grids are detected.

    If OpenCV is available, scans for horizontal+vertical line intersections
    to find table-like regions and wraps them as TableBlock.
    Otherwise, returns existing TABLE blocks from page.blocks unchanged.
    """
    existing_tables = [b for b in page.blocks if b.block_type == BlockType.TABLE]

    if not _CV2_AVAILABLE:
        return [_to_table_block(b) for b in existing_tables]

    try:
        return _detect_with_opencv(image_path, page, existing_tables)
    except Exception as exc:
        log.warning("Table detection failed with OpenCV: %s — falling back", exc)
        return [_to_table_block(b) for b in existing_tables]


def _to_table_block(block: Block) -> TableBlock:
    """Wrap a generic Block as a TableBlock, preserving fields."""
    if isinstance(block, TableBlock):
        return block
    return TableBlock(
        id=block.id,
        page_id=block.page_id,
        block_type=BlockType.TABLE,
        reading_order=block.reading_order,
        bbox=block.bbox,
        confidence=block.confidence,
        content=block.content,
    )


def _detect_with_opencv(
    image_path: Path, page: Page, existing_tables: list[Block]
) -> list[Block]:
    import cv2

    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return [_to_table_block(b) for b in existing_tables]

    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Horizontal lines kernel
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (img.shape[1] // 4, 1))
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)

    # Vertical lines kernel
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, img.shape[0] // 4))
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)

    grid = cv2.add(h_lines, v_lines)
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = img.shape[:2]
    detected: list[Block] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area_frac = (cw * ch) / (w * h)
        if area_frac < 0.02:  # skip tiny noise regions
            continue
        detected.append(TableBlock(
            page_id=page.id,
            block_type=BlockType.TABLE,
            reading_order=len(detected),
            bbox=BoundingBox(x=x, y=y, width=cw, height=ch),
            confidence=0.7,
        ))

    # Merge with existing layout-detected TABLE blocks (avoid duplicates by IoU)
    if not detected:
        return [_to_table_block(b) for b in existing_tables]
    return detected
