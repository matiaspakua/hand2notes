"""Convert VLM-transcribed Markdown into pipeline Block objects.

Parses heading levels, paragraphs, tables, and list items out of the VLM
output and assigns them to typed Block instances so the rest of the pipeline
(review, export) can handle them normally.

Blocks produced here carry `confidence=0.95` and `review_flag=False` since the
VLM output is already structured; individual blocks can still be corrected in
the review stage.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from uuid import UUID

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox, Page
from hand2notes.core_models.blocks import TableBlock

_VLM_CONFIDENCE = 0.95
_FAKE_BBOX = BoundingBox(x=0, y=0, width=1, height=1)

_H1 = re.compile(r"^#{1}\s+(.+)$")
_H2 = re.compile(r"^#{2}\s+(.+)$")
_H3 = re.compile(r"^#{3,}\s+(.+)$")
# Markdown table rows must start at column 0 (at most 3 spaces of indentation).
# Lines with tabs or deeper indentation are structural connectors, not table rows.
_TABLE_ROW = re.compile(r"^(\s{0,3})\|(.+)\|$")
_TABLE_SEP = re.compile(r"^(\s{0,3})\|[\s\-:]+(?:\|[\s\-:]+)+\|$")
_BULLET = re.compile(r"^[\-\*]\s+(.+)$")
_NUMBERED = re.compile(r"^\d+[\.\)]\s+.+$")
_NUMBERED_DOT_SPACE = re.compile(r"^\d+\s+\.\s+.+$")
_N_PAREN = re.compile(r"^\d+\)")


def _make_block(
    page_id: UUID,
    order: int,
    block_type: BlockType,
    content: str,
    page_w: int,
    page_h: int,
) -> Block:
    return Block(
        page_id=page_id,
        block_type=block_type,
        reading_order=order,
        bbox=BoundingBox(x=0, y=0, width=max(1, page_w), height=max(1, page_h)),
        confidence=_VLM_CONFIDENCE,
        review_flag=False,
        content=content,
    )


def _parse_table(rows: list[str], page_id: UUID, order: int, page_w: int, page_h: int) -> TableBlock:
    """Convert a list of raw table row strings into a TableBlock."""
    parsed: list[list[str]] = []
    for row in rows:
        if _TABLE_SEP.match(row):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        parsed.append(cells)

    headers: list[str] = []
    data_rows: list[list[str]] = []
    if parsed:
        headers = parsed[0]
        data_rows = parsed[1:]

    return TableBlock(
        page_id=page_id,
        reading_order=order,
        bbox=BoundingBox(x=0, y=0, width=max(1, page_w), height=max(1, page_h)),
        confidence=_VLM_CONFIDENCE,
        review_flag=False,
        content="\n".join(rows),
        headers=headers,
        rows=data_rows,
        reconstruction_confidence=0.9,
    )


def parse_markdown_to_blocks(
    markdown: str,
    page: Page,
) -> list[Block]:
    """Parse VLM Markdown into a list of Block objects ordered by document position.

    Tables are grouped and returned as TableBlock instances.
    All other blocks preserve the raw content string so the renderer
    can output it without re-interpreting structure.
    """
    lines = markdown.splitlines()
    blocks: list[Block] = []
    order = 0
    i = 0
    page_id = page.id
    w = max(1, page.width_px)
    h = max(1, page.height_px)

    while i < len(lines):
        line = lines[i]

        # ── Table block (collect until table ends) ───────────────────────────
        # Match against the raw line (not stripped) so tab-indented connector
        # lines are never misidentified as table rows.
        if _TABLE_ROW.match(line):
            table_rows = []
            while i < len(lines) and _TABLE_ROW.match(lines[i]):
                table_rows.append(lines[i])
                i += 1
            if table_rows:
                blocks.append(_parse_table(table_rows, page_id, order, w, h))
                order += 1
            continue

        # ── Headings ─────────────────────────────────────────────────────────
        m1 = _H1.match(line)
        if m1:
            content = m1.group(1).strip()
            # Strip bold markers the VLM sometimes wraps around section labels
            content = re.sub(r"^\*\*(.+)\*\*$", r"\1", content)
            # Numbered section labels like "1) …" or "2) …" are plain paragraphs,
            # not H1 document titles.
            btype = BlockType.PARAGRAPH if _N_PAREN.match(content) else BlockType.TITLE
            blocks.append(_make_block(page_id, order, btype, content, w, h))
            order += 1
            i += 1
            continue

        m2 = _H2.match(line)
        if m2:
            content = m2.group(1).strip()
            content = re.sub(r"^\*\*(.+)\*\*$", r"\1", content)
            btype = BlockType.PARAGRAPH if _N_PAREN.match(content) else BlockType.HEADING
            blocks.append(_make_block(page_id, order, btype, content, w, h))
            order += 1
            i += 1
            continue

        m3 = _H3.match(line)
        if m3:
            content = m3.group(1).strip()
            content = re.sub(r"^\*\*(.+)\*\*$", r"\1", content)
            blocks.append(_make_block(page_id, order, BlockType.HEADING, content, w, h))
            order += 1
            i += 1
            continue

        # ── Bullet list item ─────────────────────────────────────────────────
        if _BULLET.match(line):
            items = []
            while i < len(lines) and _BULLET.match(lines[i]):
                items.append(lines[i])
                i += 1
            blocks.append(_make_block(page_id, order, BlockType.BULLET_LIST, "\n".join(items), w, h))
            order += 1
            continue

        # ── Numbered list (standard "1." or custom "1 . " style) ────────────
        if _NUMBERED.match(line) or _NUMBERED_DOT_SPACE.match(line):
            items = []
            while i < len(lines) and (
                _NUMBERED.match(lines[i]) or _NUMBERED_DOT_SPACE.match(lines[i])
            ):
                items.append(lines[i])
                i += 1

            # If this is a single `N)` section header immediately followed by
            # structural connector lines (e.g. `\t...|` or `|--->`), collect
            # those lines into the same block so the renderer emits them without
            # a blank-line separator.
            if (len(items) == 1 and _N_PAREN.match(items[0].strip())
                    and i < len(lines) and lines[i].strip()
                    and not _NUMBERED.match(lines[i])
                    and not _NUMBERED_DOT_SPACE.match(lines[i])):
                connector_lines = []
                j = i
                while j < len(lines) and lines[j].strip():
                    nxt = lines[j]
                    if (_H1.match(nxt) or _H2.match(nxt) or _H3.match(nxt)
                            or _TABLE_ROW.match(nxt)
                            or _NUMBERED.match(nxt) or _NUMBERED_DOT_SPACE.match(nxt)
                            or _BULLET.match(nxt)):
                        break
                    connector_lines.append(nxt)
                    j += 1
                if connector_lines:
                    items.extend(connector_lines)
                    i = j

            btype = BlockType.PARAGRAPH if _N_PAREN.match(items[0].strip()) else BlockType.NUMBERED_LIST

            # If the numbered list is immediately followed (no blank line) by
            # structural / pre-formatted lines (connectors, arrows, spatial layout),
            # include them in the same block so the renderer emits them without an
            # extra blank-line separator.
            if (btype == BlockType.NUMBERED_LIST
                    and i < len(lines) and lines[i].strip()
                    and not _NUMBERED.match(lines[i])
                    and not _NUMBERED_DOT_SPACE.match(lines[i])
                    and not _BULLET.match(lines[i])
                    and not _H1.match(lines[i])
                    and not _H2.match(lines[i])
                    and not _TABLE_ROW.match(lines[i])):
                trailing = []
                j = i
                while j < len(lines) and lines[j].strip():
                    nxt = lines[j]
                    if (_H1.match(nxt) or _H2.match(nxt) or _H3.match(nxt)
                            or _TABLE_ROW.match(nxt)
                            or _NUMBERED.match(nxt) or _NUMBERED_DOT_SPACE.match(nxt)
                            or _BULLET.match(nxt)):
                        break
                    trailing.append(nxt)
                    j += 1
                if trailing:
                    items.extend(trailing)
                    i = j

            blocks.append(_make_block(page_id, order, btype, "\n".join(items), w, h))
            order += 1
            continue

        # ── Blank line ───────────────────────────────────────────────────────
        if not line.strip():
            i += 1
            continue

        # ── General paragraph / pre-formatted content ────────────────────────
        # Collect until a blank line, heading, or table starts
        para_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if (
                not next_line.strip()
                or _H1.match(next_line)
                or _H2.match(next_line)
                or _H3.match(next_line)
                or _TABLE_ROW.match(next_line)  # use raw line — indented pipes aren't tables
            ):
                break
            para_lines.append(next_line)
            i += 1
        content = "\n".join(para_lines)
        blocks.append(_make_block(page_id, order, BlockType.PARAGRAPH, content, w, h))
        order += 1

    return blocks
