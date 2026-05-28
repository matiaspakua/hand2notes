"""Markdown note renderer — template-aware, structure-preserving.

Improvements over original:
- Block merger runs first to collapse 30-50 tiny Surya blocks into logical units
- Content classifier upgrades PARAGRAPH to HEADING/TITLE where evidence supports
- Template detection decides top-level document structure
- "Página N" header only emitted for multi-page sessions AND when no title found
- Tables, diagrams, highlights, callouts rendered with full Obsidian semantics
- Consecutive list items rendered as a single Markdown list block (no blank lines between items)
"""

from __future__ import annotations

from hand2notes.core_models.blocks import DiagramBlock, TableBlock
from hand2notes.core_models.enums import BlockType, DiagramDecision, FallbackType
from hand2notes.core_models.models import Block, Page, Session, VaultConfig

from .content_classifier import apply_overrides, classify_blocks
from .front_matter import inject_front_matter
from .reconstructor import _block_to_markdown, _lines_clean, reconstruct


# ─────────────────────────────────────────────────────────────────────────────
# Diagram / Table renderers (unchanged from original)
# ─────────────────────────────────────────────────────────────────────────────

def _render_diagram_block(block: DiagramBlock, vault_root) -> str:
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

    crop = block.crop_path
    return f"![diagram crop]({crop})" if crop else ""


def _render_table_block(block: TableBlock) -> str:
    if block.reconstruction_confidence >= 0.5:
        from hand2notes.tables.md_renderer import render_markdown_table
        return render_markdown_table(block)
    if block.fallback_path:
        if block.fallback_type == FallbackType.CSV:
            caption = f" — {block.caption}" if block.caption else ""
            return f"[Table CSV]({block.fallback_path}){caption}"
        caption = block.caption or "table"
        return f"![{caption}]({block.fallback_path})"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Block rendering with visual semantics
# ─────────────────────────────────────────────────────────────────────────────

def _render_single_block(block: Block, vault_root=None) -> str:
    """Render one block to a Markdown string, applying all formatting."""
    if isinstance(block, DiagramBlock):
        return _render_diagram_block(block, vault_root)
    if isinstance(block, TableBlock):
        return _render_table_block(block)

    text = _block_to_markdown(block).strip()
    if not text:
        return ""

    # Apply URL formatting
    if block.block_type == BlockType.URL_REFERENCE:
        from hand2notes.markdown_export.url_formatter import format_url_block
        return format_url_block(block)

    # Apply visual semantics (highlight / callout) — skip if already a CALLOUT block
    vs = getattr(block, "visual_semantics", None)
    if vs and block.block_type != BlockType.CALLOUT:
        from hand2notes.markdown_export.semantics_renderer import render_block_with_semantics
        text = render_block_with_semantics(text, vs)

    return text


# ─────────────────────────────────────────────────────────────────────────────
# Consecutive-list grouping
# ─────────────────────────────────────────────────────────────────────────────

_LIST_TYPES = (BlockType.BULLET_LIST, BlockType.NUMBERED_LIST)


def _group_consecutive_lists(blocks: list[Block]) -> list[Block | list[Block]]:
    """Group consecutive same-type list blocks so they render as one list."""
    result: list[Block | list[Block]] = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if block.block_type in _LIST_TYPES:
            group = [block]
            while (i + 1 < len(blocks)
                   and blocks[i + 1].block_type == block.block_type):
                i += 1
                group.append(blocks[i])
            result.append(group if len(group) > 1 else block)
        else:
            result.append(block)
        i += 1
    return result


def _render_list_group(blocks: list[Block]) -> str:
    """Merge content of same-type list blocks into a single list."""
    from hand2notes.markdown_export.reconstructor import (
        _render_bullet_list,
        _render_numbered_list,
    )
    combined_text = "\n".join(
        (b.effective_content or "").strip() for b in blocks if (b.effective_content or "").strip()
    )
    if not combined_text:
        return ""
    if blocks[0].block_type == BlockType.NUMBERED_LIST:
        return _render_numbered_list(combined_text)
    return _render_bullet_list(combined_text)


# ─────────────────────────────────────────────────────────────────────────────
# Page rendering
# ─────────────────────────────────────────────────────────────────────────────

def _render_page(
    page: Page,
    session: Session,
    multi_page: bool,
    vault_root=None,
) -> str:
    """Render one page to a Markdown section string."""

    # ── Step 1: merge small blocks into logical units ─────────────────────────
    # Skip the spatial merger when the OCR line_grouper already produced
    # well-structured blocks (> 5 non-diagram blocks = already fine-grained).
    from hand2notes.core_models.enums import BlockType as _BT
    _text_block_count = sum(1 for b in page.blocks
                            if b.block_type not in (_BT.DIAGRAM, _BT.TABLE))
    if _text_block_count <= 5:
        from hand2notes.layout.block_merger import merge_page_blocks
        merged_blocks = merge_page_blocks(page.blocks, page.width_px, page.height_px)
    else:
        merged_blocks = list(page.blocks)

    # ── Step 2: classify blocks (infer heading / list types) ──────────────────
    overrides = classify_blocks(merged_blocks, page.height_px, page.width_px)
    apply_overrides(merged_blocks, overrides)

    # ── Step 3: sort by reading order ─────────────────────────────────────────
    sorted_blocks = sorted(merged_blocks, key=lambda b: b.reading_order)

    # ── Step 4: decide page header ────────────────────────────────────────────
    page_parts: list[str] = []

    has_title = any(b.block_type in (BlockType.TITLE, BlockType.HEADING)
                    for b in sorted_blocks)

    if multi_page:
        # Only emit page header when the page has no detected title
        if not has_title:
            page_parts.append(f"## — Página {page.sequence} —")

    # ── Step 5: render blocks, grouping consecutive lists ────────────────────
    grouped = _group_consecutive_lists(sorted_blocks)
    for item in grouped:
        if isinstance(item, list):
            rendered = _render_list_group(item)
        else:
            rendered = _render_single_block(item, vault_root)
        if rendered and rendered.strip():
            page_parts.append(rendered.strip())

    return "\n\n".join(page_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def render_note(
    session: Session,
    pages: list[Page],
    config: VaultConfig | None = None,
) -> str:
    """Render a complete Obsidian-compatible Markdown note for a session."""
    vault_root = config.vault_root if config else None
    multi_page = len(pages) > 1

    sections: list[str] = []
    for page in sorted(pages, key=lambda p: p.sequence):
        section = _render_page(page, session, multi_page, vault_root)
        if section.strip():
            sections.append(section)

    body = "\n\n---\n\n".join(sections)
    return inject_front_matter(body.strip(), session, config)
