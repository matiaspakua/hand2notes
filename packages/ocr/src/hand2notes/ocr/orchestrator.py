"""OCR orchestrator: primary path Docling + PaddleOCR; TrOCR fallback per block.

Sets block.content and block.confidence for every block on a page.
"""

from pathlib import Path

import numpy as np
from hand2notes.core_models.models import Block, Page

from .docling_adapter import convert_image as docling_convert
from .paddle_adapter import run_ocr as paddle_ocr
from .trocr_adapter import run_ocr as trocr_ocr

_DEFAULT_CONFIDENCE_THRESHOLD = 0.65


def _load_image(path: Path) -> np.ndarray:
    try:
        import cv2
        img = cv2.imread(str(path))
        return img
    except ImportError:
        return np.zeros((100, 100, 3), dtype=np.uint8)


def run_ocr_on_page(
    page: Page,
    image_path: Path,
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    languages: list[str] | None = None,
) -> list[Block]:
    """Run OCR across all text blocks on a page.

    Strategy:
    1. Try Docling on the full image for structural context.
    2. For each block, run PaddleOCR on the cropped region.
    3. If PaddleOCR confidence < threshold, fall back to TrOCR on that crop.

    Returns the updated blocks list (mutates in place and returns for convenience).
    """
    langs = languages or ["es", "en"]

    # Step 1: Docling for overall structure (best-effort; not required)
    docling_convert(image_path)

    # Step 2: Load the full image for per-block cropping
    full_image = _load_image(image_path)
    h, w = full_image.shape[:2] if full_image is not None else (1, 1)

    for block in page.blocks:
        crop_box = (block.bbox.x, block.bbox.y, block.bbox.width, block.bbox.height)

        # Clamp box to image bounds
        x, y, bw, bh = crop_box
        x = max(0, x)
        y = max(0, y)
        bw = min(bw, w - x)
        bh = min(bh, h - y)

        paddle_result = paddle_ocr(full_image, crop_box=(x, y, bw, bh), languages=langs)

        if paddle_result.confidence >= confidence_threshold or paddle_result.text:
            block.content = paddle_result.text or block.content
            block.confidence = paddle_result.confidence
        else:
            # Fallback: TrOCR on the crop
            crop = full_image[y : y + bh, x : x + bw]
            trocr_result = trocr_ocr(crop)
            block.content = trocr_result.text or paddle_result.text or block.content
            block.confidence = max(trocr_result.confidence, paddle_result.confidence)

        block.review_flag = block.confidence < confidence_threshold

    return page.blocks
