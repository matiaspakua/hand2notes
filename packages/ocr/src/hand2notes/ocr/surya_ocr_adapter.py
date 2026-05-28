"""Surya OCR adapter: text line detection + recognition for handwriting.

Uses Surya's DetectionPredictor to locate text lines and RecognitionPredictor
(via FoundationPredictor) to transcribe each line.  Much higher quality on
handwriting than Docling (designed for printed PDFs) or EasyOCR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    from surya.detection import DetectionPredictor as _DetectionPredictor
    from surya.foundation import FoundationPredictor as _FoundationPredictor
    from surya.recognition import RecognitionPredictor as _RecognitionPredictor

    _SURYA_OCR_AVAILABLE = True
except ImportError:
    _SURYA_OCR_AVAILABLE = False

_foundation: "_FoundationPredictor | None" = None
_det: "_DetectionPredictor | None" = None
_rec: "_RecognitionPredictor | None" = None

# Lines shorter than this are likely noise fragments
_MIN_TEXT_LEN = 2
# Lines below this confidence are filtered unless nothing else exists
_CONF_THRESHOLD = 0.35


@dataclass
class OcrLine:
    text: str
    confidence: float
    bbox: list[float] = field(default_factory=list)  # [x1, y1, x2, y2]


@dataclass
class PageOcrResult:
    lines: list[OcrLine]
    success: bool


def _get_predictors():
    global _foundation, _det, _rec
    if _foundation is None:
        _foundation = _FoundationPredictor()
        _det = _DetectionPredictor()
        _rec = _RecognitionPredictor(_foundation)
    return _det, _rec


def _clean_text(raw: str) -> str:
    """Normalise Surya text output: convert <br> to newline, strip artefacts."""
    text = raw.replace("<br>", "\n").replace("<br/>", "\n")
    # Remove common OCR rendering artefacts (arrow glyphs, stray punctuation)
    text = re.sub(r"[·•]\s*>", "", text)   # ·> → (remove arrow artefact)
    text = re.sub(r"->>", "→", text)        # ->> → Unicode arrow
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Keep if it contains at least one alphanumeric character
        if stripped and re.search(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]", stripped):
            lines.append(stripped)
    return "\n".join(lines)


def _is_noise(line: OcrLine) -> bool:
    """Return True for lines that are almost certainly OCR noise."""
    text = line.text.strip()
    if not text:
        return True
    if len(text) <= 1 and line.confidence < 0.6:
        return True
    # Purely symbolic / non-Latin fragments with low confidence
    if re.fullmatch(r"[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9\s\.\,\:\;\-\(\)\/]+", text) and line.confidence < 0.5:
        return True
    return False


def run_ocr_on_image(image_path: Path, languages: list[str] | None = None) -> PageOcrResult:
    """Run Surya detection + recognition on a full page image.

    Returns all detected text lines sorted top-to-bottom, left-to-right.
    """
    if not _SURYA_OCR_AVAILABLE:
        return PageOcrResult(lines=[], success=False)

    try:
        from PIL import Image as PILImage

        det_pred, rec_pred = _get_predictors()
        img = PILImage.open(image_path).convert("RGB")
        results = rec_pred([img], det_predictor=det_pred, sort_lines=True)
        ocr_result = results[0]

        lines: list[OcrLine] = []
        for tl in ocr_result.text_lines:
            raw_text = _clean_text(tl.text or "")
            if not raw_text:
                continue
            conf = float(getattr(tl, "confidence", 0.5))
            bbox = list(getattr(tl, "bbox", []) or [])
            line = OcrLine(text=raw_text, confidence=conf, bbox=bbox)
            if not _is_noise(line):
                lines.append(line)

        return PageOcrResult(lines=lines, success=True)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Surya OCR failed: %s", exc)
        return PageOcrResult(lines=[], success=False)
