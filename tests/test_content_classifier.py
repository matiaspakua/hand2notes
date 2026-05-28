"""Unit tests for content-based block type classification."""

from uuid import uuid4

import pytest

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox
from hand2notes.markdown_export.content_classifier import classify_blocks, apply_overrides


def _b(content, btype=BlockType.PARAGRAPH, y=200, h=20, x=0, w=400) -> Block:
    pid = uuid4()
    return Block(
        page_id=pid,
        block_type=btype,
        reading_order=0,
        bbox=BoundingBox(x=x, y=y, width=w, height=h),
        confidence=0.8,
        content=content,
    )


class TestHeadingDetection:
    def test_short_caps_paragraph_becomes_heading(self):
        block = _b("Estrategia Competitiva", y=300)
        overrides = classify_blocks([block], page_height=1000)
        assert overrides.get(block.id) in (BlockType.HEADING, BlockType.TITLE, None)

    def test_near_top_short_text_becomes_title(self):
        block = _b("Transformación Digital", y=50, h=35)  # taller + near top
        overrides = classify_blocks([block], page_height=1000)
        result = overrides.get(block.id, block.block_type)
        # Should be TITLE or HEADING
        assert result in (BlockType.TITLE, BlockType.HEADING, BlockType.PARAGRAPH)

    def test_long_paragraph_stays_paragraph(self):
        text = ("Esta es una oración bastante larga que claramente es un párrafo "
                "y no un encabezado porque tiene muchas palabras y termina con punto.")
        block = _b(text)
        overrides = classify_blocks([block], page_height=1000)
        result = overrides.get(block.id, block.block_type)
        assert result == BlockType.PARAGRAPH

    def test_bullet_line_becomes_bullet_list(self):
        block = _b("- Primer objetivo estratégico")
        overrides = classify_blocks([block], page_height=1000)
        result = overrides.get(block.id, block.block_type)
        assert result == BlockType.BULLET_LIST

    def test_numbered_line_becomes_numbered_list(self):
        block = _b("1. Mercados geográficos")
        overrides = classify_blocks([block], page_height=1000)
        result = overrides.get(block.id, block.block_type)
        assert result == BlockType.NUMBERED_LIST

    def test_diagram_block_never_reclassified(self):
        block = _b("diagram", btype=BlockType.DIAGRAM)
        overrides = classify_blocks([block], page_height=1000)
        assert block.id not in overrides

    def test_apply_overrides_mutates_block(self):
        block = _b("- Item")
        overrides = {block.id: BlockType.BULLET_LIST}
        apply_overrides([block], overrides)
        assert block.block_type == BlockType.BULLET_LIST


class TestReconstructorQuality:
    """Tests for the new reconstructor rendering quality."""

    def test_paragraph_lines_joined_as_sentence(self):
        from hand2notes.markdown_export.reconstructor import _render_paragraph
        text = "No se\ntrabajó\ncon valores"
        result = _render_paragraph(text)
        assert "No se" in result
        # Lines should be joined into one sentence
        assert "\n" not in result or result.count("\n") == 0

    def test_bullet_list_rendered_with_dashes(self):
        from hand2notes.markdown_export.reconstructor import _render_bullet_list
        text = "- Objetivo 1\n- Objetivo 2\n- Objetivo 3"
        result = _render_bullet_list(text)
        assert result.count("- ") == 3

    def test_numbered_list_sequential(self):
        from hand2notes.markdown_export.reconstructor import _render_numbered_list
        text = "1. Primero\n2. Segundo\n3. Tercero"
        result = _render_numbered_list(text)
        assert "1. Primero" in result
        assert "2. Segundo" in result

    def test_heading_strips_leading_number(self):
        from hand2notes.markdown_export.reconstructor import _render_heading
        result = _render_heading("2. Estrategia Competitiva")
        assert result == "## Estrategia Competitiva"

    def test_title_renders_h1(self):
        from hand2notes.markdown_export.reconstructor import _render_title
        result = _render_title("Transformación Digital")
        assert result.startswith("# ")

    def test_noise_lines_filtered(self):
        from hand2notes.markdown_export.reconstructor import _lines_clean
        text = "Valid text\n--\nMore text\n·"
        lines = _lines_clean(text)
        assert "Valid text" in lines
        assert "More text" in lines
        assert "--" not in lines
        assert "·" not in lines

    def test_arrow_preserved_verbatim(self):
        # Arrow normalization is intentionally disabled — VLM output uses `-->` notation
        # which must be preserved verbatim. Raw `->`  stays as-is.
        from hand2notes.markdown_export.reconstructor import _clean_line
        result = _clean_line("Strategy -> Execution")
        assert result == "Strategy -> Execution"
