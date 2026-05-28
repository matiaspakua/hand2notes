"""YAML front matter builder for Obsidian-compatible notes.

Generates: title, date, session, notebook, topic, tags, source_images,
confidence_summary, and custom front_matter_fields from VaultConfig.
"""

import frontmatter
from hand2notes.core_models.models import Session, VaultConfig


def build_front_matter(session: Session, config: VaultConfig | None = None) -> dict:
    """Return a dict of YAML front matter fields for the session note."""
    source_images = [str(p.source_path) for p in session.pages]

    # Compute confidence summary across all blocks in all pages
    all_confs = [
        b.confidence
        for p in session.pages
        for b in p.blocks
        if b.confidence is not None
    ]
    confidence_summary: dict = {}
    if all_confs:
        confidence_summary = {
            "mean": round(sum(all_confs) / len(all_confs), 3),
            "min": round(min(all_confs), 3),
            "max": round(max(all_confs), 3),
            "blocks": len(all_confs),
        }

    fields: dict = {
        "title": session.name,
        "date": session.created_at.strftime("%Y-%m-%d"),
        "created": session.created_at.strftime("%Y-%m-%d"),
        "session": str(session.id),
        "notebook": session.notebook,
        "source_images": source_images,
        "tags": session.tags,
    }

    if session.topic:
        fields["topic"] = session.topic

    if confidence_summary:
        fields["confidence_summary"] = confidence_summary

    # Collect color annotations from blocks with visual semantics
    color_annotations = []
    for p in session.pages:
        for b in p.blocks:
            vs = getattr(b, "visual_semantics", None)
            if vs and vs.highlight_color:
                color_annotations.append({
                    "block_id": str(b.id),
                    "color": vs.highlight_color,
                    "reading_order": b.reading_order,
                })
    if color_annotations:
        fields["color_annotations"] = color_annotations

    # Merge custom fields from vault config (these can override defaults)
    if config and config.front_matter_fields:
        fields.update(config.front_matter_fields)

    return fields


def inject_front_matter(
    markdown_body: str, session: Session, config: VaultConfig | None = None
) -> str:
    """Prepend YAML front matter to a Markdown string and return the full note."""
    fields = build_front_matter(session, config)
    post = frontmatter.Post(markdown_body, **fields)
    return frontmatter.dumps(post)
