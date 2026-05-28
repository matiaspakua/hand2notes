"""TrOCR handwriting fallback adapter.

Used for individual blocks where PaddleOCR confidence is below threshold.
Falls back gracefully when transformers / TrOCR weights are not installed.
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


@dataclass
class OCRResult:
    text: str
    confidence: float


def _load_model() -> tuple["TrOCRProcessor", "VisionEncoderDecoderModel"]:
    global _processor, _model
    if _processor is None:
        _processor = TrOCRProcessor.from_pretrained(_MODEL_NAME)
        _model = VisionEncoderDecoderModel.from_pretrained(_MODEL_NAME)
        _model.eval()  # type: ignore[union-attr]
    return _processor, _model  # type: ignore[return-value]


def run_ocr(image: np.ndarray) -> OCRResult:
    """Run TrOCR on a cropped block image (BGR numpy array).

    TrOCR is designed for single text-line inputs; pass one block crop at a time.
    """
    if not _TROCR_AVAILABLE:
        return OCRResult(text="", confidence=0.0)

    processor, model = _load_model()
    rgb = image[:, :, ::-1]  # BGR → RGB
    pil_image = PILImage.fromarray(rgb.astype(np.uint8))

    pixel_values = processor(images=pil_image, return_tensors="pt").pixel_values
    with torch.no_grad():
        generated_ids = model.generate(pixel_values)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

    # TrOCR doesn't expose per-token confidence; use a fixed heuristic
    confidence = 0.75 if text else 0.0
    return OCRResult(text=text, confidence=confidence)
