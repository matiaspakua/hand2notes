"""Visual semantics mapper.

Associates detected highlights and shapes with overlapping text blocks and
populates Block.visual_semantics with VisualSemantics model data.
"""

from hand2notes.core_models.models import Block, VisualSemantics


def _iou_overlap(block_bbox, shape_bbox: dict) -> float:
    """Compute intersection-over-union between block bbox and shape bbox."""
    bx1, by1 = block_bbox.x, block_bbox.y
    bx2, by2 = block_bbox.x + block_bbox.width, block_bbox.y + block_bbox.height

    sx = shape_bbox["x"]
    sy = shape_bbox["y"]
    sx2 = sx + shape_bbox["width"]
    sy2 = sy + shape_bbox["height"]

    ix1 = max(bx1, sx)
    iy1 = max(by1, sy)
    ix2 = min(bx2, sx2)
    iy2 = min(by2, sy2)

    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0

    block_area = (bx2 - bx1) * (by2 - by1)
    shape_area = (sx2 - sx) * (sy2 - sy)
    union = block_area + shape_area - inter
    return inter / union if union > 0 else 0.0


def map_semantics(
    blocks: list[Block],
    highlights: list[dict],
    shapes: list[dict],
    overlap_threshold: float = 0.2,
) -> None:
    """Assign VisualSemantics to blocks based on spatial overlap.

    Mutates blocks in-place; no return value.
    """
    for block in blocks:
        vs = block.visual_semantics or VisualSemantics()

        # Check highlights
        for hl in highlights:
            overlap = _iou_overlap(block.bbox, hl["bbox"])
            if overlap >= overlap_threshold:
                vs.highlight_color = hl.get("hex_color") or hl.get("color")
                break

        # Check shapes
        for shape in shapes:
            overlap = _iou_overlap(block.bbox, shape["bbox"])
            if overlap < overlap_threshold:
                continue
            shape_type = shape["shape_type"]
            if shape_type == "underline":
                vs.is_underlined = True
            elif shape_type == "box":
                vs.is_boxed = True
            elif shape_type == "circle":
                vs.is_circled = True

        # Only set if there's something meaningful
        if any([
            vs.highlight_color,
            vs.is_underlined,
            vs.is_boxed,
            vs.is_circled,
            vs.callout_label,
        ]):
            block.visual_semantics = vs
