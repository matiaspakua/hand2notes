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
    from surya.foundation import FoundationPredictor as _FoundationPredictor
    from surya.layout import LayoutPredictor as _LayoutPredictor

    _SURYA_AVAILABLE = True
except ImportError:
    _SURYA_AVAILABLE = False

# Surya ≥0.10 label map (ID_TO_LABEL values)
_BLOCK_TYPE_MAP: dict[str, BlockType] = {
    "Text": BlockType.PARAGRAPH,
    "TextInlineMath": BlockType.PARAGRAPH,
    "Handwriting": BlockType.PARAGRAPH,
    "Code": BlockType.PARAGRAPH,
    "SectionHeader": BlockType.HEADING,
    "Caption": BlockType.PARAGRAPH,
    "Footnote": BlockType.MARGINAL_NOTE,
    "Equation": BlockType.FORMULA,
    "ListItem": BlockType.BULLET_LIST,
    "PageFooter": BlockType.MARGINAL_NOTE,
    "PageHeader": BlockType.HEADING,
    "Picture": BlockType.DIAGRAM,
    "Figure": BlockType.DIAGRAM,
    "Table": BlockType.TABLE,
    "Form": BlockType.TABLE,
    "TableOfContents": BlockType.PARAGRAPH,
    # Legacy labels from older Surya versions
    "Title": BlockType.TITLE,
    "Section-header": BlockType.HEADING,
    "List-item": BlockType.BULLET_LIST,
}


def _surya_label_to_block_type(label: str) -> BlockType:
    return _BLOCK_TYPE_MAP.get(label, BlockType.PARAGRAPH)


def detect_layout(image_path: Path, page: Page) -> list[Block]:
    """Run Surya layout detection on a preprocessed image.

    Returns blocks in the order Surya produces them (reading order is assigned
    by reading_order.py in the next step.
    """
    if _SURYA_AVAILABLE:
        try:
            return _detect_with_surya(image_path, page)
        except Exception as exc:
            # Surya may be installed but incompatible with the available model
            # or its transformers version. Fallback to the geometric full-page
            # block so the pipeline remains usable.
            from logging import getLogger
            getLogger(__name__).warning(
                "Surya layout detection failed: %s — falling back to geometry", exc
            )
    return _detect_fallback(page)


def _detect_with_surya(image_path: Path, page: Page) -> list[Block]:
    from PIL import Image as PILImage

    foundation = _FoundationPredictor()
    predictor = _LayoutPredictor(foundation)
    pil_image = PILImage.open(image_path).convert("RGB")
    results = predictor([pil_image])

    blocks: list[Block] = []
    for i, layout_box in enumerate(results[0].bboxes):
        bbox = layout_box.bbox  # [x1, y1, x2, y2]
        x1, y1, x2, y2 = bbox
        label = getattr(layout_box, "label", "Text")
        block_type = _surya_label_to_block_type(label)
        # Clamp coordinates to image dimensions
        x1c = max(0, int(x1))
        y1c = max(0, int(y1))
        x2c = min(page.width_px, int(x2))
        y2c = min(page.height_px, int(y2))
        common = dict(
            page_id=page.id,
            block_type=block_type,
            reading_order=i,
            bbox=BoundingBox(
                x=x1c,
                y=y1c,
                width=max(1, x2c - x1c),
                height=max(1, y2c - y1c),
            ),
            confidence=float(getattr(layout_box, "confidence", 0.8)),
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
