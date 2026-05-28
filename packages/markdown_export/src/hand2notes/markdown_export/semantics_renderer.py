"""Obsidian visual semantics renderer.

Wraps highlighted text in ==text== notation and boxed/circled regions in
> [!NOTE] callout blocks.
"""

from hand2notes.core_models.models import VisualSemantics


def apply_highlight(text: str, visual_semantics: VisualSemantics | None) -> str:
    """Wrap text with ==highlight== if a highlight color is set."""
    if not visual_semantics or not visual_semantics.highlight_color:
        return text
    return f"=={text}=="


def apply_callout(text: str, visual_semantics: VisualSemantics | None) -> str:
    """Wrap text in an Obsidian callout block if is_boxed or is_circled."""
    if not visual_semantics:
        return text
    if not (visual_semantics.is_boxed or visual_semantics.is_circled):
        return text
    label = visual_semantics.callout_label or "NOTE"
    lines = text.split("\n")
    quoted = "\n".join(f"> {line}" for line in lines)
    return f"> [!{label}]\n{quoted}"


def render_block_with_semantics(text: str, visual_semantics: VisualSemantics | None) -> str:
    """Apply all visual semantics transformations to a text block in order."""
    if not visual_semantics:
        return text

    result = text

    # Apply highlight first (innermost)
    result = apply_highlight(result, visual_semantics)

    # Apply callout (outermost)
    result = apply_callout(result, visual_semantics)

    return result
