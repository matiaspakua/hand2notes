"""Diagram crop saver.

Always saves the cropped region image to the assets/ directory before any
reconstruction attempt. Sets DiagramBlock.crop_path. This runs unconditionally
so no diagram crop is ever lost (constitution Principle III).
"""

import logging
from pathlib import Path

from hand2notes.core_models.blocks import DiagramBlock
from hand2notes.core_models.models import Page

log = logging.getLogger(__name__)


def save_crop(
    block: DiagramBlock,
    page: Page,
    assets_dir: Path,
) -> Path:
    """Crop the diagram region from the page image and save to assets_dir.

    Uses the block's bounding box against the preprocessed (or source) image.
    Always writes the file; returns the absolute path.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    crop_filename = f"crop_{block.id}.jpg"
    crop_path = assets_dir / crop_filename

    image_path = page.preprocessed_path or page.source_path

    try:
        from PIL import Image as PILImage

        with PILImage.open(image_path) as img:
            bbox = block.bbox
            left = max(0, bbox.x)
            top = max(0, bbox.y)
            right = min(img.width, bbox.x + bbox.width)
            bottom = min(img.height, bbox.y + bbox.height)
            cropped = img.crop((left, top, right, bottom))
            cropped.save(crop_path, format="JPEG", quality=90)
    except ImportError:
        # Pillow not available — copy source image as fallback so crop_path is valid
        import shutil

        shutil.copy2(image_path, crop_path)
        log.warning("Pillow not available; saved full page as crop for block %s", block.id)
    except Exception:
        import shutil

        shutil.copy2(image_path, crop_path)
        log.exception("Crop extraction failed for block %s; saved full page", block.id)

    block.crop_path = crop_path
    return crop_path
