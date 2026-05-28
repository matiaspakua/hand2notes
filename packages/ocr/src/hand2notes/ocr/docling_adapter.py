"""Docling adapter for structured Markdown-oriented document extraction.

Used as the primary backbone for extracting structured text with semantic labels.
Falls back gracefully when docling is not installed.
"""

from dataclasses import dataclass, field
from pathlib import Path

try:
    from docling.document_converter import DocumentConverter

    _DOCLING_AVAILABLE = True
except ImportError:
    _DOCLING_AVAILABLE = False

_converter: "DocumentConverter | None" = None


@dataclass
class DoclingResult:
    markdown: str
    blocks: list[dict] = field(default_factory=list)
    success: bool = True


def _get_converter() -> "DocumentConverter":
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


def convert_image(image_path: Path) -> DoclingResult:
    """Convert a notebook page image to structured Markdown via Docling.

    Returns a DoclingResult with the Markdown string and raw block metadata.
    """
    if not _DOCLING_AVAILABLE:
        return DoclingResult(markdown="", blocks=[], success=False)

    converter = _get_converter()
    result = converter.convert(str(image_path))
    doc = result.document

    markdown = doc.export_to_markdown()
    blocks = []
    for element, _ in doc.iterate_items():
        item_dict = {}
        if hasattr(element, "label"):
            item_dict["label"] = str(element.label)
        if hasattr(element, "text"):
            item_dict["text"] = element.text
        if hasattr(element, "prov") and element.prov:
            prov = element.prov[0]
            item_dict["bbox"] = {
                "l": prov.bbox.l,
                "t": prov.bbox.t,
                "r": prov.bbox.r,
                "b": prov.bbox.b,
            }
        blocks.append(item_dict)

    return DoclingResult(markdown=markdown, blocks=blocks, success=True)
