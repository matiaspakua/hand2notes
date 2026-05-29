"""Jinja2 folder template engine for vault path generation.

Renders templates like {{notebook}}/{{date}}-{{topic}} with session fields.
Validates Jinja2 syntax on save so invalid templates are caught early.
"""

from hand2notes.core_models.models import Session
from jinja2 import BaseLoader, Environment, TemplateSyntaxError

_render_env = Environment(loader=BaseLoader(), autoescape=False)


def validate_template(template_str: str) -> None:
    """Raise ValueError if the Jinja2 template has a syntax error."""
    try:
        Environment(loader=BaseLoader()).parse(template_str)
    except TemplateSyntaxError as exc:
        raise ValueError(f"Invalid folder template: {exc}") from exc


def render_folder_path(template_str: str, session: Session) -> str:
    """Render the folder template with session fields.

    Available variables: notebook, date (YYYY-MM-DD), topic, name, session_id.
    """
    validate_template(template_str)
    tmpl = _render_env.from_string(template_str)
    date_str = session.created_at.strftime("%Y-%m-%d")
    return tmpl.render(
        notebook=session.notebook,
        date=date_str,
        topic=session.topic or "untitled",
        name=session.name,
        session_id=str(session.id),
    )
