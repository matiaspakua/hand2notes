"""Run the full hand2notes pipeline on one or more images and write the notes.

Usage:
    uv run python scripts/process_pages.py [IMAGE ...]

With no arguments, processes all four pages in inputs/transformation_digital/.
Each image is processed as its own single-page session; the resulting notes.md
is copied next to the source as <stem>_processed_actual.md for inspection.
"""

import asyncio
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs" / "transformation_digital"
OUT = ROOT / "outputs"

DEFAULT_IMAGES = [
    INPUTS / "20260527_192417.jpg",
    INPUTS / "20260527_192425.jpg",
    INPUTS / "20260527_192431.jpg",
    INPUTS / "20260527_192441.jpg",
]


def _strip_front_matter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n\n?", "", text, flags=re.DOTALL).strip()


async def process_one(image: Path, idx: int) -> tuple[str, float]:
    from hand2notes.core_models.models import Page, Session, VaultConfig
    from PIL import Image as PILImage

    from hand2notes.pipeline.orchestrator import run_pipeline

    with PILImage.open(image) as pil:
        w, h = pil.size

    session = Session(name=f"page-{idx}", notebook="transformation_digital", topic="notes")
    page = Page(session_id=session.id, source_path=image, sequence=idx, width_px=w, height_px=h)

    vault_root = OUT / "vault"
    vault_root.mkdir(parents=True, exist_ok=True)
    config = VaultConfig(
        vault_root=vault_root,
        folder_template="{{notebook}}/page-{{topic}}",
        vlm_transcription_enabled=True,
        spell_correction_enabled=False,
    )

    t0 = time.time()
    await run_pipeline(None, session, [page], config)
    elapsed = time.time() - t0

    notes = sorted(vault_root.rglob("notes.md"), key=lambda p: p.stat().st_mtime)
    content = _strip_front_matter(notes[-1].read_text(encoding="utf-8")) if notes else "(no output)"
    return content, elapsed


async def main() -> None:
    args = [Path(a) for a in sys.argv[1:]] or DEFAULT_IMAGES
    for i, image in enumerate(args, start=1):
        if not image.exists():
            print(f"!! missing: {image}")
            continue
        content, elapsed = await process_one(image, i)
        dst = image.with_name(f"{image.stem}_processed_actual.md")
        dst.write_text(content + "\n", encoding="utf-8")
        print("=" * 70)
        print(f"PAGE {i}: {image.name}  ({elapsed:.1f}s, {len(content)} chars)  -> {dst.name}")
        print("=" * 70)
        print(content)
        print()


if __name__ == "__main__":
    asyncio.run(main())
