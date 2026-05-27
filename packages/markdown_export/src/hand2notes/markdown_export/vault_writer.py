"""Vault writer: creates Obsidian vault folder structure and writes notes.md.

Default export mode is overwrite. Creates diagrams/ and assets/ subfolders.
"""

from pathlib import Path

from hand2notes.core_models.enums import ArtifactType
from hand2notes.core_models.models import ExportArtifact, Session, VaultConfig
from jinja2 import BaseLoader, Environment

_folder_env = Environment(loader=BaseLoader(), autoescape=False)


def _render_folder_path(template: str, session: Session) -> str:
    """Render the Jinja2 folder template with session fields."""
    tmpl = _folder_env.from_string(template)
    date_str = session.created_at.strftime("%Y-%m-%d")
    return tmpl.render(
        notebook=session.notebook,
        date=date_str,
        topic=session.topic or "untitled",
        name=session.name,
    )


def resolve_session_folder(config: VaultConfig, session: Session) -> Path:
    """Compute the absolute path to the session output folder."""
    if not config.vault_root:
        raise ValueError("vault_root is not configured")
    relative = _render_folder_path(config.folder_template, session)
    return config.vault_root / relative


def write_note(
    config: VaultConfig,
    session: Session,
    markdown_content: str,
) -> ExportArtifact:
    """Write notes.md into the vault folder structure.

    Creates <vault>/<notebook>/<session>/notes.md plus diagrams/ and assets/ dirs.
    Returns an ExportArtifact describing the written file.
    """
    session_folder = resolve_session_folder(config, session)
    session_folder.mkdir(parents=True, exist_ok=True)
    (session_folder / "diagrams").mkdir(exist_ok=True)
    (session_folder / "assets").mkdir(exist_ok=True)

    note_path = session_folder / "notes.md"
    note_path.write_text(markdown_content, encoding="utf-8")

    vault_relative = str(note_path.relative_to(config.vault_root))
    return ExportArtifact(
        session_id=session.id,
        artifact_type=ArtifactType.MARKDOWN,
        file_path=note_path,
        vault_relative_path=vault_relative,
    )
