"""Review payload builder.

Assembles the full review response for a page: original image URL,
preprocessed image URL, blocks with fields, Markdown preview string,
diagram previews list, overall confidence.
"""

from hand2notes.core_models.blocks import DiagramBlock
from hand2notes.core_models.models import Page, Session, VaultConfig


def build_review_payload(
    session: Session,
    page: Page,
    config: VaultConfig | None = None,
    static_base: str = "/static/crops",
) -> dict:
    """Build the review payload for a single page."""
    from hand2notes.markdown_export.renderer import render_note

    # Render Markdown preview for just this page
    try:
        markdown_preview = render_note(session, [page], config)
    except Exception:
        markdown_preview = ""

    blocks_data = []
    for b in sorted(page.blocks, key=lambda x: x.reading_order):
        block_entry: dict = {
            "block_id": str(b.id),
            "block_type": b.block_type.value,
            "content": b.corrected_content if b.corrected_content is not None else b.content,
            "original_content": b.content,
            "corrected_content": b.corrected_content,
            "confidence": b.confidence,
            "reading_order": b.reading_order,
            "review_flag": b.review_flag,
            "bbox": {
                "x": b.bbox.x,
                "y": b.bbox.y,
                "width": b.bbox.width,
                "height": b.bbox.height,
            },
        }
        if hasattr(b, "visual_semantics") and b.visual_semantics:
            vs = b.visual_semantics
            block_entry["visual_semantics"] = {
                "highlight_color": vs.highlight_color,
                "is_underlined": vs.is_underlined,
                "is_boxed": vs.is_boxed,
                "is_circled": vs.is_circled,
                "callout_label": vs.callout_label,
            }
        blocks_data.append(block_entry)

    diagram_previews = []
    for b in page.blocks:
        if isinstance(b, DiagramBlock):
            diagram_previews.append({
                "block_id": str(b.id),
                "diagram_type": b.diagram_type.value,
                "crop_path": str(b.crop_path) if b.crop_path else None,
                "generated_source_path": str(b.generated_source_path) if b.generated_source_path else None,
                "reconstruction_confidence": b.reconstruction_confidence,
                "review_decision": b.review_decision.value,
            })

    # Compute overall confidence across non-diagram blocks
    text_blocks = [b for b in page.blocks if not isinstance(b, DiagramBlock)]
    overall_conf = (
        sum(b.confidence for b in text_blocks) / len(text_blocks)
        if text_blocks else page.overall_confidence
    )

    preprocessed_url = None
    if page.preprocessed_path:
        preprocessed_url = f"file://{page.preprocessed_path}"

    return {
        "session_id": str(session.id),
        "page_id": str(page.id),
        "sequence": page.sequence,
        "source_path": str(page.source_path),
        "source_url": f"file://{page.source_path}",
        "preprocessed_path": str(page.preprocessed_path) if page.preprocessed_path else None,
        "preprocessed_url": preprocessed_url,
        "overall_confidence": round(overall_conf, 3),
        "review_status": page.review_status.value,
        "markdown_preview": markdown_preview,
        "blocks": blocks_data,
        "diagram_previews": diagram_previews,
    }
