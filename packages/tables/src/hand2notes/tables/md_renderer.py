"""Markdown table renderer.

Produces GFM-compatible | col | col | tables with left-aligned columns.
"""

from hand2notes.core_models.blocks import TableBlock


def render_markdown_table(block: TableBlock) -> str:
    """Render a TableBlock as a GFM Markdown table string."""
    if not block.headers and not block.rows:
        return ""

    headers = block.headers or [f"Col{i+1}" for i in range(len(block.rows[0]) if block.rows else 0)]
    if not headers:
        return ""

    col_widths = [max(len(h), 3) for h in headers]
    for row in block.rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    def _row(cells: list[str]) -> str:
        padded = [c.ljust(col_widths[i]) if i < len(col_widths) else c for i, c in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    separator = "| " + " | ".join("-" * w for w in col_widths) + " |"

    lines = [_row(headers), separator]
    for row in block.rows:
        lines.append(_row(row))

    if block.caption:
        lines.insert(0, f"**{block.caption}**\n")

    return "\n".join(lines)
