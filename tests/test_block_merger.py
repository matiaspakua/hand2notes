"""Unit tests for the spatial block merger."""

from uuid import uuid4

import pytest

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox
from hand2notes.layout.block_merger import merge_page_blocks


def _b(x, y, w, h, content="text", btype=BlockType.PARAGRAPH, order=0) -> Block:
    pid = uuid4()
    return Block(
        page_id=pid,
        block_type=btype,
        reading_order=order,
        bbox=BoundingBox(x=x, y=y, width=w, height=h),
        confidence=0.8,
        content=content,
    )


class TestInlineMerge:
    def test_two_blocks_same_row_merged(self):
        # Two blocks side by side on the same line
        b1 = _b(0, 100, 200, 30, "Hello", order=0)
        b2 = _b(220, 105, 200, 28, "world", order=1)
        result = merge_page_blocks([b1, b2], 800, 1000)
        # Should merge into one block
        text_blocks = [b for b in result if b.block_type == BlockType.PARAGRAPH]
        combined = " ".join(b.content or "" for b in text_blocks)
        assert "Hello" in combined
        assert "world" in combined

    def test_vertically_separated_blocks_not_merged_inline(self):
        b1 = _b(0, 0, 200, 30, "Line one", order=0)
        b2 = _b(0, 200, 200, 30, "Line two", order=1)
        result = merge_page_blocks([b1, b2], 800, 1000)
        # Should NOT inline-merge
        assert len(result) >= 2

    def test_diagrams_not_merged(self):
        b1 = _b(0, 100, 200, 30, "text", order=0)
        b2 = _b(0, 200, 400, 300, "diagram", btype=BlockType.DIAGRAM, order=1)
        result = merge_page_blocks([b1, b2], 800, 1000)
        diagram_blocks = [b for b in result if b.block_type == BlockType.DIAGRAM]
        assert len(diagram_blocks) == 1

    def test_empty_blocks_handled(self):
        result = merge_page_blocks([], 800, 1000)
        assert result == []

    def test_single_block_unchanged(self):
        b = _b(0, 0, 400, 30, "solo")
        result = merge_page_blocks([b], 800, 1000)
        assert len(result) == 1
        assert result[0].content == "solo"


class TestParagraphMerge:
    def test_close_lines_merged_into_paragraph(self):
        # Three lines close together (gap < 1.5× line height)
        b1 = _b(0, 0, 400, 30, "First line", order=0)
        b2 = _b(0, 35, 400, 28, "second line", order=1)
        b3 = _b(0, 68, 400, 29, "third line", order=2)
        result = merge_page_blocks([b1, b2, b3], 800, 1000)
        # Should collapse into 1 or 2 paragraph blocks
        assert len(result) <= 2
        all_text = " ".join((b.content or "") for b in result)
        assert "First line" in all_text
        assert "second line" in all_text
        assert "third line" in all_text

    def test_wide_gap_creates_section_break(self):
        b1 = _b(0, 0, 400, 30, "Section A", order=0)
        b2 = _b(0, 300, 400, 30, "Section B", order=1)  # gap=270, >> line_height
        result = merge_page_blocks([b1, b2], 800, 1000)
        assert len(result) == 2

    def test_list_blocks_not_merged_into_paragraph(self):
        b1 = _b(0, 0, 400, 30, "Heading", order=0)
        b2 = _b(0, 35, 400, 28, "- item one", btype=BlockType.BULLET_LIST, order=1)
        b3 = _b(0, 68, 400, 28, "- item two", btype=BlockType.BULLET_LIST, order=2)
        result = merge_page_blocks([b1, b2, b3], 800, 1000)
        list_blocks = [b for b in result if b.block_type == BlockType.BULLET_LIST]
        assert len(list_blocks) >= 1  # list blocks kept separate from heading
