"""YAML front matter builder for Obsidian-compatible notes.

Generates the minimal set of fields required for US1:
title, created, session, source_images, tags.
"""


import frontmatter
from hand2notes.core_models.models import Session, VaultConfig


def build_front_matter(session: Session, config: VaultConfig | None = None) -> dict:
    """Return a dict of YAML front matter fields for the session note."""
    source_images = [str(p.source_path) for p in session.pages]

    fields: dict = {
        "title": session.name,
        "created": session.created_at.strftime("%Y-%m-%d"),
        "session": str(session.id),
        "notebook": session.notebook,
        "source_images": source_images,
        "tags": session.tags,
    }

    if session.topic:
        fields["topic"] = session.topic

    # Merge custom fields from vault config
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
