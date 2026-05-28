"""OCR orchestrator: Docling for full-page text + TrOCR per-block fallback.

Strategy:
  1. Docling extracts structured text from the full image (fast, handles handwriting).
  2. Distribute Docling text to layout blocks by spatial overlap.
  3. For blocks with no Docling match, run trocr_adapter (microsoft/trocr-large-handwritten).
     TrOCR segments each block into lines and runs the handwriting model per line.
  4. If TrOCR is unavailable, fall back to paddle_adapter (EasyOCR).
"""

from pathlib import Path

import numpy as np
from hand2notes.core_models.models import Block, Page

from .docling_adapter import DoclingResult, convert_image as docling_convert
from .trocr_adapter import _TROCR_AVAILABLE
from .trocr_adapter import run_ocr as _trocr_ocr
from .paddle_adapter import run_ocr as _paddle_ocr


def block_ocr(image: np.ndarray, crop_box=None, languages=None):
    """Run per-block OCR: TrOCR (handwriting model) when available, else EasyOCR."""
    if _TROCR_AVAILABLE:
        return _trocr_ocr(image, crop_box=crop_box, languages=languages)
    return _paddle_ocr(image, crop_box=crop_box, languages=languages)

_DEFAULT_CONFIDENCE_THRESHOLD = 0.65


def _load_image(path: Path) -> np.ndarray:
    try:
        import cv2
        img = cv2.imread(str(path))
        return img
    except ImportError:
        return np.zeros((100, 100, 3), dtype=np.uint8)


def _overlap(bx: float, by: float, bw: float, bh: float,
             ex: float, ey: float, ew: float, eh: float,
             img_w: int, img_h: int) -> float:
    """IoU-style overlap between a block bbox and a Docling element bbox.

    Docling bbox coordinates are in the image coordinate system.
    """
    # Normalize Docling coords if they appear to be in PDF points (0-1 range not expected here)
    x1 = max(bx, ex)
    y1 = max(by, ey)
    x2 = min(bx + bw, ex + ew)
    y2 = min(by + bh, ey + eh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    union = bw * bh + ew * eh - inter
    return inter / union if union > 0 else 0.0


def _assign_docling_to_blocks(blocks: list[Block], docling: DoclingResult, img_w: int, img_h: int) -> set:
    """Assign Docling element text to the best-matching layout block.

    Returns the set of block IDs that received Docling text.
    """
    matched: set = set()
    for elem in docling.blocks:
        text = elem.get("text", "").strip()
        if not text:
            continue
        bbox = elem.get("bbox")
        if not bbox:
            continue
        # Docling bbox: {l, t, r, b} in image pixels (after Docling ≥ 2.x)
        el = float(bbox.get("l", 0))
        et = float(bbox.get("t", 0))
        er = float(bbox.get("r", img_w))
        eb = float(bbox.get("b", img_h))
        ew, eh = er - el, eb - et

        best_block: Block | None = None
        best_iou = 0.1  # minimum threshold to assign
        for block in blocks:
            iou = _overlap(block.bbox.x, block.bbox.y, block.bbox.width, block.bbox.height,
                           el, et, ew, eh, img_w, img_h)
            if iou > best_iou:
                best_iou = iou
                best_block = block

        if best_block is not None:
            prev = best_block.content or ""
            best_block.content = (prev + "\n" + text).strip() if prev else text
            best_block.confidence = max(best_block.confidence or 0.0, 0.75)
            matched.add(best_block.id)

    return matched


def run_ocr_on_page(
    page: Page,
    image_path: Path,
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    languages: list[str] | None = None,
) -> list[Block]:
    """Run OCR across all text blocks on a page.

    Returns the updated blocks list (mutates in place and returns for convenience).
    """
    langs = languages or ["es", "en"]

    # Step 1: Docling for full-page extraction (primary path — best quality)
    docling_result = docling_convert(image_path)

    full_image = _load_image(image_path)
    h, w = full_image.shape[:2] if full_image is not None else (1, 1)

    if docling_result.success and docling_result.blocks:
        matched_ids = _assign_docling_to_blocks(page.blocks, docling_result, w, h)
    elif docling_result.success and docling_result.markdown:
        # Docling ran but produced no per-element blocks: put all text in first block
        matched_ids = set()
        if page.blocks:
            page.blocks[0].content = docling_result.markdown.strip()
            page.blocks[0].confidence = 0.70
            matched_ids.add(page.blocks[0].id)
    else:
        matched_ids = set()

    # Step 2: For blocks Docling didn't cover, run per-block OCR (PaddleOCR or EasyOCR)
    for block in page.blocks:
        if block.id in matched_ids and block.confidence and block.confidence >= confidence_threshold:
            block.review_flag = False
            continue

        x = max(0, block.bbox.x)
        y = max(0, block.bbox.y)
        bw = min(block.bbox.width, w - x)
        bh = min(block.bbox.height, h - y)

        result = block_ocr(full_image, crop_box=(x, y, bw, bh), languages=langs)
        if result.text:
            prev = block.content or ""
            block.content = (prev + "\n" + result.text).strip() if prev else result.text
            block.confidence = max(block.confidence or 0.0, result.confidence)

        block.review_flag = (block.confidence or 0.0) < confidence_threshold

    return page.blocks
