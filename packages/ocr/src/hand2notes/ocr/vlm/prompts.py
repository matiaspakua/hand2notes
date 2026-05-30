# ruff: noqa: E501 — prompt strings are intentionally long, single-line instructions.
"""Prompt strings for the two-pass Qwen2.5-VL transcription.

Kept separate from the transcriber so they can be reviewed/tuned in isolation. A single
combined prompt is unstable — completeness wording suppresses diagrams while assertive
diagram wording makes the model drop text or loop — hence text and diagrams use distinct
prompts (see TRANSCRIPTION_PROMPT vs DIAGRAM_PROMPT).
"""

TRANSCRIPTION_PROMPT = (
    "You are an expert OCR system for handwritten Spanish university notes.\n\n"
    "Transcribe ALL text visible in the image as structured Markdown.\n"
    "The page is written in Spanish with some English terms.\n\n"
    "PRESERVATION:\n"
    "- Preserve ALL Spanish characters exactly: á é í ó ú ü ñ ¿ ¡\n"
    "- Preserve ALL dates, numbers, and abbreviations (ej., RRLL, RRHH, IT, MK, etc.)\n"
    "- Preserve proper names exactly (Master La Salle, Business Plan, etc.)\n"
    "- Transcribe EVERY visible word; do NOT skip or summarize any content\n"
    "- If a word is partially illegible, transcribe what you can see and note with [...]\n\n"
    "STRUCTURE:\n"
    "- Main titles at top → `# Title` (one `#` per title line)\n"
    "- Section labels like `1)` or `2)` → keep as plain text, never headings\n"
    "- Arrows: use `-->` (never → or LaTeX)\n"
    "- Vertical bar `|` as a connector → stays on its own line\n\n"
    "TABLES:\n"
    "- Use standard Markdown: `| col1 | col2 | col3 |`\n"
    "- Separator row: `| --- | --- | --- |`\n"
    "- Empty cells: `|  |`\n"
    "- Transcribe ALL cells completely; do not abbreviate table content\n\n"
    "LISTS:\n"
    "- Numbered items: `1. text` format\n"
    "- Bulleted items: `- text`\n"
    "- Preserve ALL items in a list; do not truncate\n\n"
    "SPATIAL:\n"
    "- Preserve connector trees and indentation\n"
    "- When columns appear side by side, preserve with spacing\n\n"
    "Output raw Markdown ONLY. No code fences, no explanation, no preamble."
)

DIAGRAM_PROMPT = (
    "Look only at the hand-drawn DIAGRAMS on this page: shapes (boxes, ellipses, circles,\n"
    "clouds) connected by drawn ARROWS — flowcharts, trees, process/block diagrams.\n\n"
    "For EACH such diagram, output one Mermaid flowchart code block:\n"
    "```mermaid\n"
    "flowchart TD\n"
    "    A[Gestión] --> B[Elicitación]\n"
    "    A --> C[Modelado]\n"
    "    A --> D[Análisis]\n"
    "```\n"
    "Rules:\n"
    "- Use `flowchart TD` or `flowchart LR` to match the drawing's direction.\n"
    "- Put the real Spanish words from the drawing inside the [labels].\n"
    "- Node IDs are simple ASCII letters (A, B, C…); each shape appears EXACTLY ONCE.\n"
    "- Draw exactly one `-->` edge per drawn arrow; NEVER repeat an edge or re-number a box.\n"
    "- Add edge text with `-->|texto|` only when a word labels that arrow.\n"
    "- Keep each diagram SMALL — only the shapes and arrows actually drawn.\n\n"
    "Do NOT transcribe paragraphs, lists or tables — diagrams only.\n"
    "If the page has NO arrow-connected diagram, output exactly: NONE"
)
