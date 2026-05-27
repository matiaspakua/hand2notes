"""PaddleOCR adapter for text extraction per layout block.

Handles Spanish and English. Falls back gracefully when PaddleOCR is not installed.
"""

from dataclasses import dataclass

import numpy as np

try:
    from paddleocr import PaddleOCR

    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False

_paddle_instance: "PaddleOCR | None" = None


@dataclass
class OCRResult:
    text: str
    confidence: float


def _get_paddle(languages: list[str]) -> "PaddleOCR":
    global _paddle_instance
    if _paddle_instance is None:
        # PaddleOCR lang codes: 'es' for Spanish, 'en' for English
        lang = languages[0] if languages else "en"
        _paddle_instance = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _paddle_instance


def run_ocr(
    image: np.ndarray,
    crop_box: tuple[int, int, int, int] | None = None,
    languages: list[str] | None = None,
) -> OCRResult:
    """Run PaddleOCR on an image or a cropped region.

    Args:
        image: Full-page BGR numpy array.
        crop_box: Optional (x, y, w, h) to extract a region before OCR.
        languages: Language codes in preference order (e.g. ['es', 'en']).
    """
    if not _PADDLE_AVAILABLE:
        return OCRResult(text="", confidence=0.0)

    langs = languages or ["en"]
    paddle = _get_paddle(langs)

    if crop_box is not None:
        x, y, w, h = crop_box
        region = image[y : y + h, x : x + w]
    else:
        region = image

    result = paddle.ocr(region, cls=True)

    if not result or not result[0]:
        return OCRResult(text="", confidence=0.0)

    lines = []
    confidences = []
    for line in result[0]:
        if line and len(line) >= 2:
            text_info = line[1]
            text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)
            is_seq = isinstance(text_info, (list, tuple))
            conf = float(text_info[1]) if is_seq and len(text_info) > 1 else 0.8
            lines.append(text.strip())
            confidences.append(conf)

    combined_text = "\n".join(lines)
    mean_confidence = float(np.mean(confidences)) if confidences else 0.0
    return OCRResult(text=combined_text, confidence=mean_confidence)
