"""PNG export for generated diagram source files.

Attempts to invoke CLI tools (plantuml, drawio) to render a PNG alongside
the source file. Both tools are optional — if absent, a warning is logged and
None is returned so the caller can gracefully degrade.

Install hints:
  PlantUML: https://plantuml.com/download  (requires Java)
  draw.io:  https://github.com/jgraph/drawio-desktop/releases  (headless export)
"""

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def export_plantuml_png(puml_path: Path) -> Path | None:
    """Render a .puml file to PNG using the local plantuml CLI.

    Returns the PNG Path on success, None if the tool is unavailable or fails.
    """
    plantuml_cmd = shutil.which("plantuml")
    if not plantuml_cmd:
        log.warning(
            "plantuml CLI not found — PNG export skipped for %s. "
            "Install PlantUML (requires Java): https://plantuml.com/download",
            puml_path.name,
        )
        return None

    png_path = puml_path.with_suffix(".png")
    try:
        result = subprocess.run(
            [plantuml_cmd, "-tpng", str(puml_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log.warning(
                "plantuml exited %d for %s: %s",
                result.returncode,
                puml_path.name,
                (result.stderr or result.stdout).strip(),
            )
            return None
        if png_path.exists():
            log.info("PlantUML PNG exported: %s (%d bytes)", png_path.name, png_path.stat().st_size)
            return png_path
        log.warning("plantuml ran successfully but PNG not found at %s", png_path)
        return None
    except subprocess.TimeoutExpired:
        log.error("plantuml timed out (>30s) rendering %s", puml_path.name)
        return None
    except Exception as exc:
        log.error("Unexpected error running plantuml for %s: %s", puml_path.name, exc)
        return None


def export_drawio_png(drawio_path: Path) -> Path | None:
    """Render a .drawio file to PNG using the draw.io desktop CLI.

    Returns the PNG Path on success, None if the tool is unavailable or fails.
    draw.io desktop supports headless export via:
      drawio --export --format png --output out.png in.drawio
    """
    drawio_cmd = shutil.which("drawio") or shutil.which("draw.io")
    if not drawio_cmd:
        log.warning(
            "drawio CLI not found — PNG export skipped for %s. "
            "Install draw.io desktop: https://github.com/jgraph/drawio-desktop/releases",
            drawio_path.name,
        )
        return None

    png_path = drawio_path.with_suffix(".png")
    try:
        result = subprocess.run(
            [
                drawio_cmd,
                "--export",
                "--format", "png",
                "--output", str(png_path),
                str(drawio_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log.warning(
                "drawio exited %d for %s: %s",
                result.returncode,
                drawio_path.name,
                (result.stderr or result.stdout).strip(),
            )
            return None
        if png_path.exists():
            log.info("draw.io PNG exported: %s (%d bytes)", png_path.name, png_path.stat().st_size)
            return png_path
        log.warning("drawio ran successfully but PNG not found at %s", png_path)
        return None
    except subprocess.TimeoutExpired:
        log.error("drawio timed out (>30s) rendering %s", drawio_path.name)
        return None
    except Exception as exc:
        log.error("Unexpected error running drawio for %s: %s", drawio_path.name, exc)
        return None
