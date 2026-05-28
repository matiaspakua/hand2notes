"""Structure reconstructor: maps BlockType to Markdown elements.

Preserves reading order. Uses effective_content (corrected_content > content).
"""

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block


def _block_to_markdown(block: Block) -> str:
    """Convert a single block to its Markdown representation."""
    text = block.effective_content or ""

    match block.block_type:
        case BlockType.TITLE:
            return f"# {text}" if text else ""
        case BlockType.HEADING:
            return f"## {text}" if text else ""
        case BlockType.PARAGRAPH:
            return text
        case BlockType.BULLET_LIST:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(f"- {line}" for line in lines) if lines else ""
        case BlockType.NUMBERED_LIST:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(f"{i + 1}. {line}" for i, line in enumerate(lines)) if lines else ""
        case BlockType.CALLOUT:
            return f"> [!NOTE]\n> {text}" if text else ""
        case BlockType.MARGINAL_NOTE:
            return f"> {text}" if text else ""
        case BlockType.URL_REFERENCE:
            url = text.strip()
            return f"[{url}]({url})" if url else ""
        case BlockType.FORMULA:
            return f"$${text}$$" if text else ""
        case BlockType.DIAGRAM | BlockType.TABLE:
            # Diagrams and tables handled by their respective modules;
            # reconstructor emits a placeholder if they land here.
            if block.crop_path:
                return f"![{block.block_type.value}]({block.crop_path})"
            return f"<!-- {block.block_type.value} block -->"
        case _:
            return text


def reconstruct(blocks: list[Block]) -> str:
    """Convert an ordered list of blocks to a single Markdown string."""
    sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)
    parts = []
    for block in sorted_blocks:
        md = _block_to_markdown(block)
        if md:
            parts.append(md)

    return "\n\n".join(parts)
