"""Image import, validation, and format normalization.

Accepts JPG, JPEG, PNG, and HEIC (converted to JPEG before downstream processing).
Validates file size (< 50 MB).
Returns a Page model with source_path, width_px, height_px populated.
"""

import logging
from pathlib import Path
from uuid import UUID

from hand2notes.core_models.models import Page
from PIL import Image

log = logging.getLogger(__name__)

_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


class ImportError(Exception):
    """Raised when an image cannot be imported."""


def _convert_heic_to_jpeg(heic_path: Path) -> Path:
    """Convert HEIC/HEIF to JPEG and return the JPEG path."""
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError as err:
        raise ImportError(
            "pillow-heif is required to import HEIC files. "
            "Install with: pip install pillow-heif"
        ) from err

    jpeg_path = heic_path.with_suffix(".jpg")
    with Image.open(heic_path) as img:
        img = img.convert("RGB")
        img.save(jpeg_path, format="JPEG", quality=92)
    log.info("Converted HEIC %s → %s", heic_path, jpeg_path)
    return jpeg_path


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
    """Validate and import a single image, returning a Page with metadata populated.

    HEIC/HEIF files are converted to JPEG before returning; the resulting Page
    points to the converted JPEG path so downstream stages always receive JPEG.
    """
    validate_image(path)

    # Convert HEIC/HEIF to JPEG before downstream processing
    if path.suffix.lower() in {".heic", ".heif"}:
        path = _convert_heic_to_jpeg(path)

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
