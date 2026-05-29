# ruff: noqa: E501 — prompt strings are intentionally long, single-line instructions.
"""Prompt strings for the two-pass Qwen2.5-VL transcription.

Kept separate from the transcriber so they can be reviewed/tuned in isolation. A single
combined prompt is unstable — completeness wording suppresses diagrams while assertive
diagram wording makes the model drop text or loop — hence text and diagrams use distinct
prompts (see TRANSCRIPTION_PROMPT vs DIAGRAM_PROMPT).
"""

TRANSCRIPTION_PROMPT = (
    "You are an expert OCR system for handwritten university notes.\n\n"
    "Carefully read EVERY word in the image and transcribe it as structured Markdown.\n"
    "The page is written in Spanish. Preserve all Spanish characters exactly.\n\n"
    "STRUCTURE RULES:\n"
    "- The main titles at the top (underlined or highlighted) → use `# Title` (one `#` per title line)\n"
    "- Section labels like `1)` or `2)` → keep as plain text, never use `##` headings\n"
    "- After a section label, preserve any connector block on the next lines unchanged\n"
    "- Arrows: write as `-->` or `--->` (NEVER Unicode → or LaTeX \\rightarrow)\n"
    "- A vertical bar `|` used as a connector → stays on its own line with the same indentation\n\n"
    "TABLE RULES (for any grid/table visible in the image):\n"
    "- Use standard Markdown: `| col1 | col2 | col3 |`\n"
    "- Separator row uses only dashes: `| --- | --- | --- |`\n"
    "- Empty cells: `|  |`\n\n"
    "LIST RULES:\n"
    "- Numbered items: `N . text` format (digit SPACE dot SPACE text)\n"
    "- Bulleted items: `- text`\n\n"
    "SPATIAL LAYOUT:\n"
    "- Preserve indented/hierarchical connector trees using tabs\n"
    "- When two columns of text appear side by side at the bottom, preserve spacing\n\n"
    "IGNORE: dates, page numbers, and timestamps in margins/corners.\n\n"
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
