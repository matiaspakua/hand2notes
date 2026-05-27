"""Markdown note renderer using Jinja2.

Concatenates reconstructed blocks into a final Markdown string and injects
YAML front matter. Diagram/table references are embedded at reading-order position.
"""

from hand2notes.core_models.models import Block, Page, Session, VaultConfig
from jinja2 import BaseLoader, Environment

from .front_matter import inject_front_matter
from .reconstructor import reconstruct

_NOTE_TEMPLATE = """\
{{ body }}
"""

_env = Environment(loader=BaseLoader(), autoescape=False)
_template = _env.from_string(_NOTE_TEMPLATE)


def render_note(
    session: Session,
    pages: list[Page],
    config: VaultConfig | None = None,
) -> str:
    """Render a complete Obsidian-compatible Markdown note for a session.

    Args:
        session: The session whose pages are being exported.
        pages: Ordered list of pages with populated blocks.
        config: Vault configuration (used for front matter customization).

    Returns:
        Full Markdown string including YAML front matter.
    """
    all_blocks: list[Block] = []
    for page in sorted(pages, key=lambda p: p.sequence):
        all_blocks.extend(page.blocks)

    body = reconstruct(all_blocks)
    markdown_body = _template.render(body=body).strip()
    return inject_front_matter(markdown_body, session, config)
