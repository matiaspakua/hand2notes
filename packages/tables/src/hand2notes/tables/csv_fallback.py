"""CSV fallback exporter for low-confidence tables.

Writes table-{n}.csv to the assets/ directory when reconstruction_confidence < 0.5.
"""

import csv
import logging
from pathlib import Path

from hand2notes.core_models.blocks import TableBlock
from hand2notes.core_models.enums import FallbackType

log = logging.getLogger(__name__)


def export_csv(block: TableBlock, assets_dir: Path, index: int = 0) -> Path:
    """Write the table as CSV and update block.fallback_type/fallback_path.

    Returns the path to the written CSV file.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    csv_path = assets_dir / f"table-{index}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if block.headers:
            writer.writerow(block.headers)
        for row in block.rows:
            writer.writerow(row)

    block.fallback_type = FallbackType.CSV
    block.fallback_path = csv_path
    return csv_path
