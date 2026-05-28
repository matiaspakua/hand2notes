"""PaddleOCR adapter for text extraction per layout block.

Primary engine: PaddleOCR (requires paddlepaddle).
Fallback engine: EasyOCR (pure-Python, no extra native deps).
Falls back gracefully when neither is installed.
"""

from dataclasses import dataclass

import numpy as np

try:
    from paddleocr import PaddleOCR as _PaddleOCR
    import paddle as _paddle  # noqa: F401 — import confirms native lib is present

    _PADDLE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _PADDLE_AVAILABLE = False

try:
    import easyocr as _easyocr

    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False

_paddle_instance: "_PaddleOCR | None" = None
_easyocr_reader: "_easyocr.Reader | None" = None


@dataclass
class OCRResult:
    text: str
    confidence: float


def _get_paddle(languages: list[str]) -> "_PaddleOCR":
    global _paddle_instance
    if _paddle_instance is None:
        lang = languages[0] if languages else "en"
        _paddle_instance = _PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _paddle_instance


def _get_easyocr(languages: list[str]) -> "_easyocr.Reader":
    global _easyocr_reader
    if _easyocr_reader is None:
        # EasyOCR uses ISO 639-1 codes; map 'es' → 'es', 'en' → 'en'
        langs = [lg for lg in languages if lg in ("en", "es", "fr", "de", "pt")] or ["en"]
        _easyocr_reader = _easyocr.Reader(langs, gpu=False, verbose=False)
    return _easyocr_reader


def _run_paddle(region: np.ndarray, languages: list[str]) -> OCRResult:
    paddle = _get_paddle(languages)
    result = paddle.ocr(region, cls=True)
    if not result or not result[0]:
        return OCRResult(text="", confidence=0.0)
    lines, confidences = [], []
    for line in result[0]:
        if line and len(line) >= 2:
            text_info = line[1]
            text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)
            conf = float(text_info[1]) if isinstance(text_info, (list, tuple)) and len(text_info) > 1 else 0.8
            lines.append(text.strip())
            confidences.append(conf)
    return OCRResult(
        text="\n".join(lines),
        confidence=float(np.mean(confidences)) if confidences else 0.0,
    )


def _run_easyocr(region: np.ndarray, languages: list[str]) -> OCRResult:
    reader = _get_easyocr(languages)
    results = reader.readtext(region, detail=1, paragraph=False)
    if not results:
        return OCRResult(text="", confidence=0.0)
    lines = [text for (_, text, _) in results]
    confidences = [conf for (_, _, conf) in results]
    return OCRResult(
        text="\n".join(lines),
        confidence=float(np.mean(confidences)) if confidences else 0.0,
    )


def run_ocr(
    image: np.ndarray,
    crop_box: tuple[int, int, int, int] | None = None,
    languages: list[str] | None = None,
) -> OCRResult:
    """Run OCR on an image or a cropped region.

    Uses PaddleOCR when available, falls back to EasyOCR.

    Args:
        image: Full-page BGR numpy array.
        crop_box: Optional (x, y, w, h) to extract a region before OCR.
        languages: Language codes in preference order (e.g. ['es', 'en']).
    """
    if not _PADDLE_AVAILABLE and not _EASYOCR_AVAILABLE:
        return OCRResult(text="", confidence=0.0)

    langs = languages or ["en"]

    if crop_box is not None:
        x, y, w, h = crop_box
        region = image[y : y + h, x : x + w]
    else:
        region = image

    if region.size == 0:
        return OCRResult(text="", confidence=0.0)

    if _PADDLE_AVAILABLE:
        return _run_paddle(region, langs)
    return _run_easyocr(region, langs)
