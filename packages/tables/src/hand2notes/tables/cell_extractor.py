"""Table cell extraction and grid reconstruction.

Uses OpenCV line grid detection to find cell bounding boxes, then runs OCR
on each cell using the OCR orchestrator.
"""

import logging
from pathlib import Path

from hand2notes.core_models.blocks import TableBlock
from hand2notes.core_models.models import Page

log = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


def extract_cells(
    block: TableBlock,
    page: Page,
    image_path: Path,
) -> TableBlock:
    """Extract headers and rows from a table block via cell-level OCR.

    Returns the block with headers and rows populated. On failure, sets
    reconstruction_confidence=0 so fallback logic can kick in.
    """
    if not _CV2_AVAILABLE:
        log.warning("OpenCV not available — cannot extract table cells")
        block.reconstruction_confidence = 0.0
        return block

    try:
        return _extract_with_opencv(block, image_path)
    except Exception as exc:
        log.warning("Cell extraction failed for block %s: %s", block.id, exc)
        block.reconstruction_confidence = 0.0
        return block


def _extract_with_opencv(block: TableBlock, image_path: Path) -> TableBlock:
    import cv2
    import numpy as np

    img = cv2.imread(str(image_path))
    if img is None:
        block.reconstruction_confidence = 0.0
        return block

    bbox = block.bbox
    roi = img[bbox.y:bbox.y + bbox.height, bbox.x:bbox.x + bbox.width]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h, w = gray.shape[:2]

    # Find horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 5, 1))
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
    h_proj = np.sum(h_lines, axis=1)
    row_splits = _find_splits(h_proj, h)

    # Find vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 5))
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)
    v_proj = np.sum(v_lines, axis=0)
    col_splits = _find_splits(v_proj, w)

    if len(row_splits) < 2 or len(col_splits) < 2:
        block.reconstruction_confidence = 0.3
        return block

    # Build cell grid (row_splits × col_splits pairs define cell boundaries)
    cells: list[list[str]] = []
    for r in range(len(row_splits) - 1):
        row_cells: list[str] = []
        y1, y2 = row_splits[r], row_splits[r + 1]
        for c in range(len(col_splits) - 1):
            x1, x2 = col_splits[c], col_splits[c + 1]
            cell_img = roi[y1:y2, x1:x2]
            text = _ocr_cell(cell_img)
            row_cells.append(text)
        cells.append(row_cells)

    if not cells:
        block.reconstruction_confidence = 0.2
        return block

    block.headers = cells[0]
    block.rows = cells[1:]
    block.reconstruction_confidence = 0.8
    return block


def _find_splits(projection, size: int) -> list[int]:
    """Find row/column boundaries from a projection profile."""
    threshold = projection.max() * 0.3
    in_line = False
    splits = [0]
    for i, val in enumerate(projection):
        if not in_line and val > threshold:
            in_line = True
            splits.append(i)
        elif in_line and val <= threshold:
            in_line = False
    splits.append(size)
    return sorted(set(splits))


def _ocr_cell(cell_image) -> str:
    """Run OCR on a single cell image; return empty string on failure."""
    try:
        import numpy as np
        from PIL import Image as PILImage
        pil = PILImage.fromarray(cell_image)

        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            result = ocr.ocr(np.array(pil), cls=False)
            if result and result[0]:
                return " ".join(line[1][0] for line in result[0] if line).strip()
        except ImportError:
            pass

        # Minimal fallback: return empty string
        return ""
    except Exception:
        return ""
