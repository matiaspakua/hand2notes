"""OCR orchestrator: Surya OCR (primary) + TrOCR (fallback).

Strategy:
  1. Surya DetectionPredictor finds text lines across the full page.
  2. Surya RecognitionPredictor transcribes each line (best quality for handwriting).
  3. Lines are assigned to Surya layout blocks by spatial IoU overlap.
  4. Blocks with no Surya OCR coverage fall back to TrOCR line-segmentation.
  5. Confidence threshold gates the review_flag for each block.
"""

from pathlib import Path

import numpy as np
from hand2notes.core_models.models import Block, Page

from .surya_ocr_adapter import OcrLine, run_ocr_on_image, _SURYA_OCR_AVAILABLE
from .trocr_adapter import _TROCR_AVAILABLE
from .trocr_adapter import run_ocr as _trocr_ocr
from .paddle_adapter import run_ocr as _paddle_ocr

_DEFAULT_CONFIDENCE_THRESHOLD = 0.55


def _fallback_ocr(image: np.ndarray, crop_box=None, languages=None):
    """Per-block fallback: TrOCR when available, else EasyOCR."""
    if _TROCR_AVAILABLE:
        return _trocr_ocr(image, crop_box=crop_box, languages=languages)
    return _paddle_ocr(image, crop_box=crop_box, languages=languages)


def _line_containment(bx: float, by: float, bw: float, bh: float,
                       lx1: float, ly1: float, lx2: float, ly2: float) -> float:
    """Fraction of a Surya line that falls within a layout block.

    Returns overlap_area / line_area.  This is robust to large blocks that
    would suppress a normal IoU score because the union is dominated by the
    block's huge area.
    """
    ix1 = max(bx, lx1)
    iy1 = max(by, ly1)
    ix2 = min(bx + bw, lx2)
    iy2 = min(by + bh, ly2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    line_area = max(1.0, (lx2 - lx1) * (ly2 - ly1))
    return inter / line_area


def _assign_surya_lines_to_blocks(
    blocks: list[Block],
    lines: list[OcrLine],
    img_w: int,
    img_h: int,
) -> set:
    """Assign OCR lines to the best-matching layout block by line containment.

    A line is matched to the block that contains the largest fraction of the
    line's bounding box area.  Returns block IDs that received at least one line.
    """
    matched: set = set()

    for line in lines:
        if not line.bbox or len(line.bbox) < 4:
            continue
        lx1, ly1, lx2, ly2 = line.bbox[0], line.bbox[1], line.bbox[2], line.bbox[3]

        best_block: Block | None = None
        best_score = 0.3  # minimum containment fraction to count as a match
        for block in blocks:
            score = _line_containment(
                block.bbox.x, block.bbox.y, block.bbox.width, block.bbox.height,
                lx1, ly1, lx2, ly2,
            )
            if score > best_score:
                best_score = score
                best_block = block

        if best_block is not None:
            prev = best_block.content or ""
            new_text = line.text.strip()
            best_block.content = (prev + "\n" + new_text).strip() if prev else new_text
            best_block.confidence = max(best_block.confidence or 0.0, line.confidence)
            matched.add(best_block.id)

    return matched


def _load_image(path: Path) -> np.ndarray:
    try:
        import cv2
        return cv2.imread(str(path))
    except ImportError:
        return np.zeros((100, 100, 3), dtype=np.uint8)


def run_ocr_on_page(
    page: Page,
    image_path: Path,
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    languages: list[str] | None = None,
) -> list[Block]:
    """Run OCR across all text blocks on a page.

    Mutates blocks in place (sets content, confidence, review_flag).
    Returns the updated blocks list for convenience.
    """
    langs = languages or ["es", "en"]

    full_image = _load_image(image_path)
    h, w = full_image.shape[:2] if full_image is not None and full_image.size > 0 else (1, 1)

    # --- Primary: Surya full-page OCR ---
    if _SURYA_OCR_AVAILABLE:
        surya_result = run_ocr_on_image(image_path, languages=langs)
        if surya_result.success and surya_result.lines:
            # If layout gave us too few large blocks, rebuild structure from OCR lines
            coarse_layout = _is_coarse_layout(page.blocks, h)
            if coarse_layout:
                from .line_grouper import rebuild_blocks_from_lines
                new_blocks = rebuild_blocks_from_lines(
                    surya_result.lines, page.id, w, h, existing_blocks=page.blocks
                )
                page.blocks = new_blocks
                for block in page.blocks:
                    block.review_flag = (block.confidence or 0.0) < confidence_threshold
                return page.blocks
            else:
                matched_ids = _assign_surya_lines_to_blocks(page.blocks, surya_result.lines, w, h)
        else:
            matched_ids = set()
    else:
        matched_ids = set()

    # --- Fallback: per-block TrOCR / EasyOCR for blocks Surya missed ---
    for block in page.blocks:
        already_covered = block.id in matched_ids and (block.confidence or 0.0) >= confidence_threshold
        if already_covered:
            block.review_flag = False
            continue

        x = max(0, block.bbox.x)
        y = max(0, block.bbox.y)
        bw = min(block.bbox.width, w - x)
        bh = min(block.bbox.height, h - y)

        if bw > 0 and bh > 0 and full_image is not None and full_image.size > 0:
            result = _fallback_ocr(full_image, crop_box=(x, y, bw, bh), languages=langs)
            if result.text:
                prev = block.content or ""
                block.content = (prev + "\n" + result.text).strip() if prev else result.text
                block.confidence = max(block.confidence or 0.0, result.confidence)

        block.review_flag = (block.confidence or 0.0) < confidence_threshold

    return page.blocks


def _is_coarse_layout(blocks: list[Block], page_height: int) -> bool:
    """Return True when layout detection produced too-large blocks for structure inference."""
    from hand2notes.core_models.enums import BlockType as BT
    text_blocks = [b for b in blocks if b.block_type not in (BT.DIAGRAM, BT.TABLE)]
    if not text_blocks:
        return False
    avg_h = sum(b.bbox.height for b in text_blocks) / len(text_blocks)
    # If average text-block height > 50% of page height → layout is too coarse
    return avg_h > page_height * 0.3 or len(text_blocks) <= 2
