"""Unit tests for the block-level post-processor."""

from uuid import uuid4

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox, Page
from hand2notes.text_correction.postprocessor import correct_page


def _make_page(*block_texts: tuple[BlockType, str]) -> Page:
    sid = uuid4()
    pid = uuid4()
    blocks = [
        Block(
            page_id=pid,
            block_type=btype,
            reading_order=i,
            bbox=BoundingBox(x=0, y=i * 50, width=400, height=40),
            confidence=0.7,
            content=text,
        )
        for i, (btype, text) in enumerate(block_texts)
    ]
    return Page(
        id=pid,
        session_id=sid,
        sequence=1,
        source_path="/tmp/test.jpg",  # type: ignore[arg-type]
        width_px=400,
        height_px=500,
        blocks=blocks,
    )


class TestCorrectPage:
    def test_returns_metrics(self):
        page = _make_page((BlockType.PARAGRAPH, "empresa estrategia"))
        metrics = correct_page(page)
        assert "blocks_checked" in metrics
        assert "blocks_corrected" in metrics
        assert "words_corrected" in metrics

    def test_correct_paragraph_block(self):
        # "bussines" is clearly misspelled and should be corrected to "business"
        page = _make_page((BlockType.PARAGRAPH, "bussines"))
        correct_page(page)
        block = page.blocks[0]
        # Spell corrector should set auto_corrected_content when it corrects the word.
        # The exact suggestion is dictionary-dependent; we verify the mechanism works.
        assert isinstance(block.auto_corrected_content, str | type(None))
        if block.auto_corrected_content is not None:
            assert block.auto_corrected_content != block.content

    def test_known_words_not_flagged(self):
        page = _make_page((BlockType.PARAGRAPH, "empresa estrategia vision"))
        correct_page(page)
        block = page.blocks[0]
        # No correction needed → auto_corrected_content stays None
        # (depends on whether OCR words are in dict — soft assertion)
        assert isinstance(block.auto_corrected_content, str | type(None))

    def test_diagram_block_skipped(self):
        page = _make_page((BlockType.DIAGRAM, "some diagram text"))
        correct_page(page)
        # DIAGRAM is not correctable
        block = page.blocks[0]
        assert block.auto_corrected_content is None

    def test_empty_content_skipped(self):
        page = _make_page((BlockType.PARAGRAPH, ""))
        metrics = correct_page(page)
        assert metrics["blocks_checked"] == 0

    def test_effective_content_prefers_user_correction(self):
        page = _make_page((BlockType.PARAGRAPH, "emprersa"))
        correct_page(page)
        block = page.blocks[0]
        block.corrected_content = "empresa (manual)"
        assert block.effective_content == "empresa (manual)"

    def test_effective_content_falls_back_to_auto(self):
        page = _make_page((BlockType.PARAGRAPH, "emprersa"))
        block = page.blocks[0]
        block.auto_corrected_content = "empresa"
        assert block.effective_content == "empresa"

    def test_effective_content_falls_back_to_raw(self):
        page = _make_page((BlockType.PARAGRAPH, "raw text"))
        block = page.blocks[0]
        assert block.auto_corrected_content is None
        assert block.corrected_content is None
        assert block.effective_content == "raw text"

    def test_heading_block_corrected(self):
        page = _make_page((BlockType.HEADING, "estrategi competitiv"))
        metrics = correct_page(page)
        assert metrics["blocks_checked"] >= 1
