"""Vault writer: creates Obsidian vault folder structure and writes notes.md.

Supports three export modes:
- overwrite (default): replaces existing notes.md and companion files
- versioned: writes notes-{timestamp}.md alongside existing versions
- merge: appends new page content to existing notes.md

Writes .puml and .drawio diagram source files from DiagramBlock artifacts.
Stale file cleanup runs for overwrite mode.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from hand2notes.core_models.blocks import DiagramBlock, TableBlock
from hand2notes.core_models.enums import ArtifactType, DiagramFormat, ExportMode, FallbackType
from hand2notes.core_models.models import ExportArtifact, Page, Session, VaultConfig
from jinja2 import BaseLoader, Environment

_folder_env = Environment(loader=BaseLoader(), autoescape=False)


def _render_folder_path(template: str, session: Session) -> str:
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
    pages: list[Page] | None = None,
) -> list[ExportArtifact]:
    """Write the note and diagram sources to the vault using the configured export mode.

    Returns a list of ExportArtifact records for all written files.
    """
    export_mode = config.export_mode

    if export_mode == ExportMode.VERSIONED:
        return _write_versioned(config, session, markdown_content, pages)
    elif export_mode == ExportMode.MERGE:
        return _write_merge(config, session, markdown_content, pages)
    else:
        return _write_overwrite(config, session, markdown_content, pages)


def _setup_dirs(session_folder: Path) -> tuple[Path, Path]:
    """Create session/diagrams/ and session/assets/ directories."""
    diagrams_dir = session_folder / "diagrams"
    assets_dir = session_folder / "assets"
    session_folder.mkdir(parents=True, exist_ok=True)
    diagrams_dir.mkdir(exist_ok=True)
    assets_dir.mkdir(exist_ok=True)
    return diagrams_dir, assets_dir


def _write_diagram_artifacts(
    config: VaultConfig,
    session: Session,
    pages: list[Page] | None,
    diagrams_dir: Path,
    assets_dir: Path,
) -> list[ExportArtifact]:
    """Copy diagram source files and crops; return ExportArtifact list."""
    artifacts: list[ExportArtifact] = []
    if not pages:
        return artifacts

    for page in pages:
        for block in page.blocks:
            if not isinstance(block, DiagramBlock):
                continue

            if block.crop_path and Path(block.crop_path).exists():
                dest_crop = assets_dir / Path(block.crop_path).name
                if Path(block.crop_path) != dest_crop:
                    shutil.copy2(block.crop_path, dest_crop)
                vr = str(dest_crop.relative_to(config.vault_root))
                artifacts.append(ExportArtifact(
                    session_id=session.id,
                    page_id=page.id,
                    artifact_type=ArtifactType.IMAGE_ASSET,
                    file_path=dest_crop,
                    vault_relative_path=vr,
                ))

            if block.generated_source_path and Path(block.generated_source_path).exists():
                src_file = Path(block.generated_source_path)
                dest_src = diagrams_dir / src_file.name
                if src_file != dest_src:
                    shutil.copy2(src_file, dest_src)
                artifact_type = (
                    ArtifactType.PLANTUML
                    if block.generated_format == DiagramFormat.PLANTUML
                    else ArtifactType.DRAWIO
                )
                vr = str(dest_src.relative_to(config.vault_root))
                artifacts.append(ExportArtifact(
                    session_id=session.id,
                    page_id=page.id,
                    artifact_type=artifact_type,
                    file_path=dest_src,
                    vault_relative_path=vr,
                ))

            # Copy companion PNG if the CLI export succeeded
            png_path = getattr(block, "generated_png_path", None)
            if png_path and Path(png_path).exists():
                dest_png = diagrams_dir / Path(png_path).name
                if Path(png_path) != dest_png:
                    shutil.copy2(png_path, dest_png)
                vr_png = str(dest_png.relative_to(config.vault_root))
                artifacts.append(ExportArtifact(
                    session_id=session.id,
                    page_id=page.id,
                    artifact_type=ArtifactType.IMAGE_ASSET,
                    file_path=dest_png,
                    vault_relative_path=vr_png,
                ))

    # Copy table fallback files (CSV and image crops)
    if pages:
        for page in pages:
            for block in page.blocks:
                if not isinstance(block, TableBlock):
                    continue
                if block.fallback_path and Path(block.fallback_path).exists():
                    dest = assets_dir / Path(block.fallback_path).name
                    if Path(block.fallback_path) != dest:
                        shutil.copy2(block.fallback_path, dest)
                    artifact_type = (
                        ArtifactType.CSV
                        if block.fallback_type == FallbackType.CSV
                        else ArtifactType.IMAGE_ASSET
                    )
                    vr = str(dest.relative_to(config.vault_root))
                    artifacts.append(ExportArtifact(
                        session_id=session.id,
                        page_id=page.id,
                        artifact_type=artifact_type,
                        file_path=dest,
                        vault_relative_path=vr,
                    ))

    return artifacts


def _write_overwrite(
    config: VaultConfig,
    session: Session,
    markdown_content: str,
    pages: list[Page] | None,
) -> list[ExportArtifact]:
    """Replace existing notes.md and companions; remove stale files."""
    session_folder = resolve_session_folder(config, session)
    diagrams_dir, assets_dir = _setup_dirs(session_folder)

    # Track current artifact paths for stale-file removal
    note_path = session_folder / "notes.md"
    note_path.write_text(markdown_content, encoding="utf-8")
    vr_note = str(note_path.relative_to(config.vault_root))
    current_paths = {note_path}

    artifacts = [ExportArtifact(
        session_id=session.id,
        artifact_type=ArtifactType.MARKDOWN,
        file_path=note_path,
        vault_relative_path=vr_note,
    )]

    diagram_artifacts = _write_diagram_artifacts(config, session, pages, diagrams_dir, assets_dir)
    artifacts.extend(diagram_artifacts)
    current_paths.update(a.file_path for a in diagram_artifacts)

    # Remove stale files from diagrams/ and assets/ not in current export
    for subdir in (diagrams_dir, assets_dir):
        for existing in subdir.iterdir():
            if existing.is_file() and existing not in current_paths:
                existing.unlink()

    return artifacts


def _write_versioned(
    config: VaultConfig,
    session: Session,
    markdown_content: str,
    pages: list[Page] | None,
) -> list[ExportArtifact]:
    """Write notes-{timestamp}.md alongside existing versions."""
    session_folder = resolve_session_folder(config, session)
    diagrams_dir, assets_dir = _setup_dirs(session_folder)

    ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    note_path = session_folder / f"notes-{ts}.md"
    note_path.write_text(markdown_content, encoding="utf-8")
    vr_note = str(note_path.relative_to(config.vault_root))

    artifacts = [ExportArtifact(
        session_id=session.id,
        artifact_type=ArtifactType.MARKDOWN,
        file_path=note_path,
        vault_relative_path=vr_note,
    )]
    artifacts.extend(_write_diagram_artifacts(config, session, pages, diagrams_dir, assets_dir))
    return artifacts


def _write_merge(
    config: VaultConfig,
    session: Session,
    markdown_content: str,
    pages: list[Page] | None,
) -> list[ExportArtifact]:
    """Append new page content to existing notes.md."""
    session_folder = resolve_session_folder(config, session)
    diagrams_dir, assets_dir = _setup_dirs(session_folder)

    note_path = session_folder / "notes.md"
    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8")
        # Strip front matter from the new content before appending to avoid duplicates
        import re
        stripped = re.sub(r"^---\n.*?\n---\n", "", markdown_content, flags=re.DOTALL).strip()
        merged = existing.rstrip() + "\n\n---\n\n" + stripped
        note_path.write_text(merged, encoding="utf-8")
    else:
        note_path.write_text(markdown_content, encoding="utf-8")

    vr_note = str(note_path.relative_to(config.vault_root))
    artifacts = [ExportArtifact(
        session_id=session.id,
        artifact_type=ArtifactType.MARKDOWN,
        file_path=note_path,
        vault_relative_path=vr_note,
    )]
    artifacts.extend(_write_diagram_artifacts(config, session, pages, diagrams_dir, assets_dir))
    return artifacts
