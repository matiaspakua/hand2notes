"""Reading order assignment for detected blocks.

Uses Surya reading order when available; falls back to a geometric top-to-bottom
left-to-right sort that works well for single-column notebook pages.
"""

from hand2notes.core_models.models import Block

try:
    from surya.model.ordering.model import load_model, load_processor
    from surya.ordering import batch_ordering

    _SURYA_AVAILABLE = True
except ImportError:
    _SURYA_AVAILABLE = False


def assign_reading_order(blocks: list[Block], image_width: int, image_height: int) -> list[Block]:
    """Return blocks with reading_order indices set.

    Tries Surya ordering first; falls back to geometric sort.
    Mutates the list in place and also returns it for convenience.
    """
    if _SURYA_AVAILABLE and blocks:
        return _order_with_surya(blocks, image_width, image_height)
    return _order_geometric(blocks)


def _order_with_surya(blocks: list[Block], image_width: int, image_height: int) -> list[Block]:
    from PIL import Image as PILImage

    model = load_model()
    processor = load_processor()

    # Build bbox list in [x1, y1, x2, y2] format expected by Surya
    bboxes = [
        [b.bbox.x, b.bbox.y, b.bbox.x + b.bbox.width, b.bbox.y + b.bbox.height]
        for b in blocks
    ]

    dummy_image = PILImage.new("RGB", (image_width, image_height), color=(255, 255, 255))
    predictions = batch_ordering([dummy_image], [bboxes], model, processor)

    order_map = {i: pred for i, pred in enumerate(predictions[0].bboxes)}
    for i, block in enumerate(blocks):
        surya_order = order_map.get(i)
        block.reading_order = int(surya_order.position) if surya_order else i

    blocks.sort(key=lambda b: b.reading_order)
    return blocks


def _order_geometric(blocks: list[Block]) -> list[Block]:
    """Top-to-bottom, left-to-right ordering based on bounding box centroids."""
    # Divide page into rough columns: left half vs right half
    # For single-column notebook pages this is essentially top-to-bottom
    blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))
    for i, block in enumerate(blocks):
        block.reading_order = i
    return blocks
