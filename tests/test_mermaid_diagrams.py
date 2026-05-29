"""Unit tests for VLM Mermaid-diagram handling (no Ollama required).

Covers the sanitizer that protects against the two VLM failure modes —
runaway edge loops and duplicate/re-numbered nodes — and the parser path that
turns a ```mermaid fence into a DIAGRAM block rendered verbatim.
"""

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Page, Session
from hand2notes.ocr.qwen_vl_transcriber import (
    _close_dangling_fence,
    _sanitize_mermaid_blocks,
)
from hand2notes.ocr.vlm_blocks_parser import parse_markdown_to_blocks


def _wrap(body: str) -> str:
    return f"```mermaid\n{body}\n```"


def test_good_diagram_is_deduped_and_kept():
    body = (
        "flowchart TD\n"
        "    A[Gestión] --> B[Elicitación]\n"
        "    A --> C[Modelado]\n"
        "    A --> D[Análisis]\n"
        "    A --> B[Elicitación]\n"  # duplicate edge
    )
    out = _sanitize_mermaid_blocks(_wrap(body))
    assert "```mermaid" in out
    assert out.count("-->") == 3  # duplicate removed
    assert "Gestión" in out and "Elicitación" in out


def test_renumbered_duplicate_nodes_merge():
    body = (
        "flowchart TD\n"
        "    A[Gestión] --> B[Tarea]\n"
        "    A2[Gestión] --> B2[Tarea]\n"  # same labels, re-numbered ids
    )
    out = _sanitize_mermaid_blocks(_wrap(body))
    # Both lines describe the same edge once labels are canonicalised.
    assert out.count("-->") == 1


def test_runaway_loop_is_discarded_but_text_kept():
    body = "flowchart TD\n" + "".join(
        f"    A -->|PE D| B{i}[ICTA]\n    A -->|PE E| C{i}[Auditoría]\n" for i in range(40)
    )
    text = f"# Business Plan\n\n{_wrap(body)}\n\nkeep this text"
    out = _sanitize_mermaid_blocks(text)
    assert "```mermaid" not in out  # degenerate diagram dropped
    assert "# Business Plan" in out and "keep this text" in out


def test_unterminated_fence_is_closed_then_discarded():
    body = "flowchart TD\n" + "".join(f"    A -->|x| B{i}[ICTA]\n" for i in range(30))
    truncated = f"# Title\n\n```mermaid\n{body}"  # no closing fence
    out = _sanitize_mermaid_blocks(_close_dangling_fence(truncated))
    assert "```mermaid" not in out
    assert "# Title" in out


def test_parser_emits_diagram_block_for_mermaid_fence():
    session = Session(name="t", notebook="t", topic="t")
    page = Page(session_id=session.id, sequence=1,
                source_path=__import__("pathlib").Path("x.png"), width_px=10, height_px=10)
    md = "# Title\n\n" + _wrap("flowchart TD\n    A[Uno] --> B[Dos]")
    blocks = parse_markdown_to_blocks(md, page)
    diagram_blocks = [b for b in blocks if b.block_type == BlockType.DIAGRAM]
    assert len(diagram_blocks) == 1
    assert diagram_blocks[0].content.startswith("```mermaid")
    assert "flowchart TD" in diagram_blocks[0].content
