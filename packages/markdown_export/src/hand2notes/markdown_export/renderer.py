"""Markdown note renderer using Jinja2.

Concatenates reconstructed blocks into a final Markdown string and injects
YAML front matter. Diagram/table references are embedded at reading-order position.
"""

from hand2notes.core_models.blocks import DiagramBlock, TableBlock
from hand2notes.core_models.enums import DiagramDecision, FallbackType
from hand2notes.core_models.models import Block, Page, Session, VaultConfig
from jinja2 import BaseLoader, Environment

from .front_matter import inject_front_matter
from .reconstructor import reconstruct

_NOTE_TEMPLATE = """\
{{ body }}
"""

_env = Environment(loader=BaseLoader(), autoescape=False)
_template = _env.from_string(_NOTE_TEMPLATE)


def _render_diagram_block(block: DiagramBlock, vault_root) -> str:
    """Return an Obsidian embed or image reference for a diagram block."""
    decision = block.review_decision

    if decision == DiagramDecision.REJECTED:
        crop = block.crop_path
        if crop and vault_root:
            try:
                from pathlib import Path
                rel = Path(crop).relative_to(vault_root)
                return f"![[{rel}]]"
            except ValueError:
                pass
        return f"![diagram crop]({crop})" if crop else ""

    # Approved or pending: prefer generated source file
    if block.generated_source_path:
        src = block.generated_source_path
        if vault_root:
            try:
                from pathlib import Path
                rel = Path(src).relative_to(vault_root)
                return f"![[{rel}]]"
            except ValueError:
                pass
        return f"![[{src.name}]]"

    # Fallback to crop when no source was generated
    crop = block.crop_path
    if crop:
        return f"![diagram crop]({crop})"
    return ""


def _apply_block_semantics(text: str, block) -> str:
    """Apply VisualSemantics (highlights, callouts) and URL formatting to block text."""
    from hand2notes.core_models.enums import BlockType

    # URL blocks get hyperlink formatting
    if block.block_type == BlockType.URL_REFERENCE:
        from hand2notes.markdown_export.url_formatter import format_url_block
        return format_url_block(block)

    # Visual semantics (highlights, callouts)
    vs = getattr(block, "visual_semantics", None)
    if vs:
        from hand2notes.markdown_export.semantics_renderer import render_block_with_semantics
        return render_block_with_semantics(text, vs)

    return text


def _render_table_block(block: TableBlock) -> str:
    """Render a TableBlock: Markdown table when confidence >= 0.5, else fallback reference."""
    if block.reconstruction_confidence >= 0.5:
        from hand2notes.tables.md_renderer import render_markdown_table
        return render_markdown_table(block)

    # Fallback: reference CSV or image crop
    if block.fallback_path:
        name = block.fallback_path.name
        if block.fallback_type == FallbackType.CSV:
            caption = f" — {block.caption}" if block.caption else ""
            return f"[Table CSV]({block.fallback_path}){caption}"
        else:
            caption = block.caption or "table"
            return f"![{caption}]({block.fallback_path})"
    return ""


def render_note(
    session: Session,
    pages: list[Page],
    config: VaultConfig | None = None,
) -> str:
    """Render a complete Obsidian-compatible Markdown note for a session.

    Args:
        session: The session whose pages are being exported.
        pages: Ordered list of pages with populated blocks.
        config: Vault configuration (used for front matter customization).

    Returns:
        Full Markdown string including YAML front matter.
    """
    vault_root = config.vault_root if config else None
    sections: list[str] = []

    for page in sorted(pages, key=lambda p: p.sequence):
        page_parts: list[str] = []
        for block in sorted(page.blocks, key=lambda b: b.reading_order):
            if isinstance(block, DiagramBlock):
                rendered = _render_diagram_block(block, vault_root)
                if rendered:
                    page_parts.append(rendered)
            elif isinstance(block, TableBlock):
                rendered = _render_table_block(block)
                if rendered:
                    page_parts.append(rendered)
            else:
                text = reconstruct([block]).strip()
                if text:
                    text = _apply_block_semantics(text, block)
                    if text:
                        page_parts.append(text)
        if page_parts:
            sections.append("\n\n".join(page_parts))

    body = "\n\n---\n\n".join(sections)
    markdown_body = _template.render(body=body).strip()
    return inject_front_matter(markdown_body, session, config)
