"""Image crop fallback for irregularly structured tables.

Saves a crop image to assets/ when a table is too irregular for Markdown or CSV.
"""

import logging
from pathlib import Path

from hand2notes.core_models.blocks import TableBlock
from hand2notes.core_models.enums import FallbackType
from hand2notes.core_models.models import Page

log = logging.getLogger(__name__)


def export_image_crop(
    block: TableBlock,
    page: Page,
    assets_dir: Path,
    index: int = 0,
) -> Path:
    """Crop the table region and save to assets/table-{n}-crop.jpg.

    Updates block.fallback_type and block.fallback_path.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    crop_path = assets_dir / f"table-{index}-crop.jpg"
    image_path = page.preprocessed_path or page.source_path

    try:
        from PIL import Image as PILImage
        with PILImage.open(image_path) as img:
            b = block.bbox
            left = max(0, b.x)
            top = max(0, b.y)
            right = min(img.width, b.x + b.width)
            bottom = min(img.height, b.y + b.height)
            cropped = img.crop((left, top, right, bottom))
            cropped.save(crop_path, format="JPEG", quality=90)
    except ImportError:
        import shutil
        shutil.copy2(image_path, crop_path)
        log.warning("Pillow not available; saved full page as table crop for block %s", block.id)
    except Exception:
        import shutil
        shutil.copy2(image_path, crop_path)
        log.exception("Image crop failed for table block %s; saved full page", block.id)

    block.fallback_type = FallbackType.IMAGE
    block.fallback_path = crop_path
    return crop_path
