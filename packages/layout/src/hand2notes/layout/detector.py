"""Layout region detection using Surya.

Falls back to a geometric full-page block when Surya is not installed, so the
pipeline is runnable in environments without the heavy ML dependency.

Diagram regions (Surya label "Figure") are returned as DiagramBlock instances
with crop_path unset — the crop is saved in the detect_diagrams pipeline stage.
"""

from pathlib import Path

from hand2notes.core_models.blocks import DiagramBlock
from hand2notes.core_models.enums import BlockType, DiagramType
from hand2notes.core_models.models import Block, BoundingBox, Page

try:
    from surya.detection import batch_text_detection
    from surya.model.detection.model import load_model, load_processor

    _SURYA_AVAILABLE = True
except ImportError:
    _SURYA_AVAILABLE = False

_BLOCK_TYPE_MAP: dict[str, BlockType] = {
    "Title": BlockType.TITLE,
    "Section-header": BlockType.HEADING,
    "Text": BlockType.PARAGRAPH,
    "List-item": BlockType.BULLET_LIST,
    "Table": BlockType.TABLE,
    "Figure": BlockType.DIAGRAM,
    "Caption": BlockType.PARAGRAPH,
    "Footnote": BlockType.MARGINAL_NOTE,
    "Formula": BlockType.FORMULA,
}


def _surya_label_to_block_type(label: str) -> BlockType:
    return _BLOCK_TYPE_MAP.get(label, BlockType.PARAGRAPH)


def detect_layout(image_path: Path, page: Page) -> list[Block]:
    """Run Surya layout detection on a preprocessed image.

    Returns blocks in the order Surya produces them (reading order is assigned
    by reading_order.py in the next step).
    """
    if _SURYA_AVAILABLE:
        return _detect_with_surya(image_path, page)
    return _detect_fallback(page)


def _detect_with_surya(image_path: Path, page: Page) -> list[Block]:
    from PIL import Image as PILImage

    model = load_model()
    processor = load_processor()

    pil_image = PILImage.open(image_path).convert("RGB")
    predictions = batch_text_detection([pil_image], model, processor)

    blocks: list[Block] = []
    for i, text_line in enumerate(predictions[0].bboxes):
        bbox = text_line.bbox  # [x1, y1, x2, y2]
        x1, y1, x2, y2 = bbox
        label = getattr(text_line, "label", "Text")
        block_type = _surya_label_to_block_type(label)
        common = dict(
            page_id=page.id,
            block_type=block_type,
            reading_order=i,
            bbox=BoundingBox(
                x=int(x1),
                y=int(y1),
                width=int(x2 - x1),
                height=int(y2 - y1),
            ),
            confidence=float(getattr(text_line, "confidence", 0.8)),
        )
        if block_type == BlockType.DIAGRAM:
            # crop_path will be set by the crop_saver in the detect_diagrams stage
            blocks.append(DiagramBlock(**common, crop_path=page.source_path))
        else:
            blocks.append(Block(**common))
    return blocks


def _detect_fallback(page: Page) -> list[Block]:
    """Return a single full-page block when Surya is unavailable."""
    return [
        Block(
            page_id=page.id,
            block_type=BlockType.PARAGRAPH,
            reading_order=0,
            bbox=BoundingBox(x=0, y=0, width=page.width_px, height=page.height_px),
            confidence=0.5,
        )
    ]
