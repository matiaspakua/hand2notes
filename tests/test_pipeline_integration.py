"""Integration test: create session → upload → process → review → export.

Requires a sample image in samples/ directory. Skipped if no sample is available.
"""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
SAMPLE_IMAGES = [f for f in SAMPLES_DIR.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png"} and not f.name.startswith(".")]


@pytest.mark.skipif(not SAMPLE_IMAGES, reason="No sample images in samples/ directory")
def test_pipeline_end_to_end(tmp_path):
    """Full pipeline from image import to vault export."""
    from hand2notes.core_models.enums import SessionStatus
    from hand2notes.core_models.models import VaultConfig
    from hand2notes.ingestion.importer import import_images
    from hand2notes.core_models.models import Session

    sample_image = SAMPLE_IMAGES[0]

    session = Session(
        name="Integration Test Session",
        notebook="test-notebook",
        topic="integration",
        tags=["test"],
    )

    pages = import_images([sample_image], session.id)
    assert len(pages) == 1
    assert pages[0].width_px > 0
    assert pages[0].height_px > 0

    vault_root = tmp_path / "test-vault"
    vault_root.mkdir()

    config = VaultConfig(
        vault_root=vault_root,
        folder_template="{{notebook}}/{{date}}-{{topic}}",
        export_mode="overwrite",
    )

    # Run pipeline
    async def _run():
        from hand2notes.pipeline.orchestrator import run_pipeline
        events = []
        result = await run_pipeline(
            db=None,
            session=session,
            pages=pages,
            config=config,
            on_progress=events.append,
        )
        return result, events

    result_session, events = asyncio.run(_run())

    # Verify pipeline ran
    stage_names = {e.get("stage") for e in events if e.get("event") == "stage_completed"}
    assert "import" in stage_names
    assert "preprocess" in stage_names

    # Verify export artifact
    notes_files = list(vault_root.rglob("notes*.md"))
    assert len(notes_files) >= 1, f"No notes.md found in vault: {list(vault_root.rglob('*'))}"

    notes_content = notes_files[0].read_text()
    assert len(notes_content) > 10, "notes.md appears empty"

    print(f"Integration test passed: {notes_files[0]}")
