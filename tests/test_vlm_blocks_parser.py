"""Unit tests for parse_markdown_to_blocks — the VLM-Markdown → Block converter."""

from pathlib import Path

from hand2notes.core_models.blocks import TableBlock
from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Page, Session
from hand2notes.ocr.vlm_blocks_parser import parse_markdown_to_blocks


def _page() -> Page:
    session = Session(name="t", notebook="t", topic="t")
    return Page(session_id=session.id, sequence=1,
                source_path=Path("x.png"), width_px=100, height_px=200)


def _types(md: str) -> list[BlockType]:
    return [b.block_type for b in parse_markdown_to_blocks(md, _page())]


def test_h1_is_title():
    blocks = parse_markdown_to_blocks("# Master LaSalle", _page())
    assert blocks[0].block_type == BlockType.TITLE
    assert blocks[0].content == "Master LaSalle"


def test_numbered_section_label_is_paragraph_not_title():
    # "1) ..." is a section label, not a document title, even as an H1.
    blocks = parse_markdown_to_blocks("# 1) Misión", _page())
    assert blocks[0].block_type == BlockType.PARAGRAPH


def test_markdown_table_becomes_table_block():
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    blocks = parse_markdown_to_blocks(md, _page())
    tables = [b for b in blocks if isinstance(b, TableBlock)]
    assert len(tables) == 1
    assert tables[0].headers == ["A", "B"]
    assert tables[0].rows == [["1", "2"]]


def test_bullet_list_block():
    md = "- uno\n- dos\n- tres"
    blocks = parse_markdown_to_blocks(md, _page())
    assert blocks[0].block_type == BlockType.BULLET_LIST
    assert blocks[0].content.count("\n") == 2


def test_numbered_list_block():
    md = "1 . uno\n2 . dos"
    assert _types(md) == [BlockType.NUMBERED_LIST]


def test_tab_indented_pipe_is_not_a_table():
    # Tab-indented connector lines must not be misread as Markdown table rows.
    md = "\t| connector"
    blocks = parse_markdown_to_blocks(md, _page())
    assert not any(isinstance(b, TableBlock) for b in blocks)


def test_mermaid_fence_is_diagram_block():
    md = "```mermaid\nflowchart TD\n    A[Uno] --> B[Dos]\n```"
    blocks = parse_markdown_to_blocks(md, _page())
    assert blocks[0].block_type == BlockType.DIAGRAM
    assert "flowchart TD" in blocks[0].content


def test_mixed_document_order_preserved():
    md = "# Title\n\nParagraph text\n\n- a\n- b\n\n| X | Y |\n| --- | --- |"
    types = _types(md)
    assert types[0] == BlockType.TITLE
    assert BlockType.BULLET_LIST in types
    assert any(t == BlockType.TABLE for t in types)
    # reading_order is sequential
    blocks = parse_markdown_to_blocks(md, _page())
    orders = [b.reading_order for b in blocks]
    assert orders == sorted(orders)
