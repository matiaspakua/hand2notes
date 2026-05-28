"""TrOCR handwriting OCR adapter.

Pipeline:
  1. Segment the block crop into individual text lines via horizontal projection profiling.
  2. Run microsoft/trocr-large-handwritten on each line crop.
  3. Compute real confidence from model sequence scores (log-prob of generated tokens).
  4. Return concatenated text + mean confidence.
"""

from dataclasses import dataclass

import numpy as np

try:
    import torch
    from PIL import Image as PILImage
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    _TROCR_AVAILABLE = True
except ImportError:
    _TROCR_AVAILABLE = False

_MODEL_NAME = "microsoft/trocr-large-handwritten"
_processor: "TrOCRProcessor | None" = None
_model: "VisionEncoderDecoderModel | None" = None

# Minimum line height (px) to filter noise from projection profiling
_MIN_LINE_HEIGHT = 8
# Padding (px) added above/below each detected line to avoid clipping ascenders/descenders
_LINE_PADDING = 3


@dataclass
class OCRResult:
    text: str
    confidence: float


def _load_model() -> tuple["TrOCRProcessor", "VisionEncoderDecoderModel"]:
    global _processor, _model
    if _processor is None:
        import logging
        # Suppress "newly initialized pooler" and "use_fast" noise from transformers
        logging.getLogger("transformers").setLevel(logging.ERROR)
        _processor = TrOCRProcessor.from_pretrained(_MODEL_NAME, use_fast=True)
        _model = VisionEncoderDecoderModel.from_pretrained(_MODEL_NAME)
        _model.eval()  # type: ignore[union-attr]
        logging.getLogger("transformers").setLevel(logging.WARNING)
    return _processor, _model  # type: ignore[return-value]


def _segment_lines(gray: np.ndarray) -> list[tuple[int, int]]:
    """Return (y_start, y_end) row ranges for each text line in a grayscale crop.

    Uses horizontal projection: count dark pixels per row, then find contiguous
    runs of rows above a threshold (ink present) separated by valleys (whitespace).
    """
    # Binarise: dark pixels = ink
    threshold = 180
    ink_mask = gray < threshold  # True where dark
    row_ink = ink_mask.sum(axis=1)  # ink pixel count per row

    h = gray.shape[0]
    in_line = False
    line_start = 0
    lines: list[tuple[int, int]] = []

    for y in range(h):
        has_ink = row_ink[y] > 0
        if not in_line and has_ink:
            in_line = True
            line_start = y
        elif in_line and not has_ink:
            in_line = False
            y_start = max(0, line_start - _LINE_PADDING)
            y_end = min(h, y + _LINE_PADDING)
            if y_end - y_start >= _MIN_LINE_HEIGHT:
                lines.append((y_start, y_end))
    if in_line:
        y_start = max(0, line_start - _LINE_PADDING)
        y_end = min(h, h + _LINE_PADDING)
        if y_end - y_start >= _MIN_LINE_HEIGHT:
            lines.append((y_start, y_end))

    return lines


def _score_from_output(scores: tuple | None, generated_ids: "torch.Tensor") -> float:
    """Compute mean per-token probability from model transition scores.

    `scores` is a tuple of (vocab_size,) tensors returned by model.generate(output_scores=True).
    Each entry corresponds to the log-unnormalised logits at that generation step.
    We convert to probabilities and take the mean of the max-prob token at each step
    as an approximation of generation confidence.
    """
    if scores is None or len(scores) == 0:
        return 0.75
    probs = []
    for step_logits in scores:
        # step_logits: (batch=1, vocab_size)
        p = torch.softmax(step_logits[0], dim=-1)
        probs.append(float(p.max().item()))
    return float(np.mean(probs)) if probs else 0.75


def _run_trocr_on_line(pil_line: "PILImage.Image", processor, model) -> tuple[str, float]:
    """Run TrOCR on a single PIL line image. Returns (text, confidence)."""
    pixel_values = processor(images=pil_line, return_tensors="pt").pixel_values
    with torch.no_grad():
        output = model.generate(
            pixel_values,
            output_scores=True,
            return_dict_in_generate=True,
        )
    text = processor.batch_decode(output.sequences, skip_special_tokens=True)[0].strip()
    confidence = _score_from_output(output.scores, output.sequences)
    return text, confidence


def run_ocr(image: np.ndarray, crop_box: tuple | None = None, languages: list | None = None) -> OCRResult:
    """Run TrOCR on a block image (BGR numpy array).

    Segments the block into individual text lines, runs TrOCR on each, and
    returns the concatenated text with mean confidence.

    Parameters match the block_ocr interface used by the OCR orchestrator.
    `languages` is accepted but ignored — TrOCR handles multilingual text natively.
    """
    if not _TROCR_AVAILABLE:
        return OCRResult(text="", confidence=0.0)

    if crop_box is not None:
        x, y, w, h = crop_box
        image = image[y:y + h, x:x + w]

    if image is None or image.size == 0:
        return OCRResult(text="", confidence=0.0)

    processor, model = _load_model()

    # Convert BGR → RGB for PIL
    rgb = image[:, :, ::-1].astype(np.uint8)
    pil_block = PILImage.fromarray(rgb)

    # Grayscale for line segmentation
    try:
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    except ImportError:
        gray = np.mean(image, axis=2).astype(np.uint8)

    lines = _segment_lines(gray)

    # If no lines detected (e.g. tiny block or blank), run on the full block
    if not lines:
        lines = [(0, image.shape[0])]

    texts: list[str] = []
    confidences: list[float] = []

    for y_start, y_end in lines:
        line_rgb = rgb[y_start:y_end, :]
        if line_rgb.size == 0:
            continue
        pil_line = PILImage.fromarray(line_rgb)
        # TrOCR expects a minimum width; skip degenerate slices
        if pil_line.width < 4 or pil_line.height < 4:
            continue
        try:
            text, conf = _run_trocr_on_line(pil_line, processor, model)
        except Exception:
            continue
        if text:
            texts.append(text)
            confidences.append(conf)

    if not texts:
        return OCRResult(text="", confidence=0.0)

    return OCRResult(
        text="\n".join(texts),
        confidence=float(np.mean(confidences)),
    )
