"""Markdown hyperlink formatter for detected URL blocks."""

import re

from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def format_url_block(block: Block) -> str:
    """Render a URL_REFERENCE block as a Markdown hyperlink.

    Returns `[url](url)` for full URLs or `<url>` for partial/bare URLs.
    """
    text = (block.corrected_content or block.content or "").strip()
    if not text:
        return ""

    if block.block_type != BlockType.URL_REFERENCE:
        return text

    if text.startswith("http://") or text.startswith("https://"):
        return f"[{text}]({text})"
    elif text.startswith("www."):
        url = f"https://{text}"
        return f"[{text}]({url})"
    else:
        return f"<{text}>"
