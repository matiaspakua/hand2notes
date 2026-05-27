"""Image import, validation, and format normalization.

Accepts JPG, JPEG, PNG. Validates file size (< 50 MB).
Returns a Page model with source_path, width_px, height_px populated.
"""

from pathlib import Path
from uuid import UUID

from hand2notes.core_models.models import Page
from PIL import Image

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


class ImportError(Exception):
    """Raised when an image cannot be imported."""


def validate_image(path: Path) -> None:
    """Raise ImportError if the file is not an importable image."""
    if not path.exists():
        raise ImportError(f"File not found: {path}")
    if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise ImportError(
            f"Unsupported format '{path.suffix}'. Supported: {_SUPPORTED_SUFFIXES}"
        )
    size = path.stat().st_size
    if size > _MAX_SIZE_BYTES:
        raise ImportError(
            f"File exceeds 50 MB limit ({size / 1024 / 1024:.1f} MB): {path}"
        )


def import_image(path: Path, session_id: UUID, sequence: int) -> Page:
    """Validate and import a single image, returning a Page with metadata populated."""
    validate_image(path)

    with Image.open(path) as img:
        width_px, height_px = img.size

    return Page(
        session_id=session_id,
        sequence=sequence,
        source_path=path.resolve(),
        width_px=width_px,
        height_px=height_px,
    )


def import_images(paths: list[Path], session_id: UUID) -> list[Page]:
    """Import multiple images in order, returning one Page per image."""
    pages: list[Page] = []
    for i, path in enumerate(paths, start=1):
        pages.append(import_image(path, session_id, sequence=i))
    return pages
