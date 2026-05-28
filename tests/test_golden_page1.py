"""Golden fixture test for page_1: 20260527_192417.jpg → page_1_processed.md.

This test is the primary quality gate for the full pipeline on the first
annotated golden example. It runs the complete pipeline end-to-end and
compares the content (front matter stripped) against the expected fixture.

Pass threshold: ≥ 99% similarity (SequenceMatcher ratio).

Requires Ollama to be running with at least one supported VLM:
  - qwen2.5vl:7b  (preferred)
  - gemma4:e4b    (fallback)

Skip conditions:
  - Input image not present in inputs/transformation_digital/
  - Ollama not reachable
"""

import asyncio
import difflib
import re
import shutil
from pathlib import Path

import pytest

_INPUTS_DIR = Path(__file__).parent.parent / "inputs" / "transformation_digital"
_INPUT_IMAGE = _INPUTS_DIR / "20260527_192417.jpg"
_EXPECTED_FILE = _INPUTS_DIR / "page_1_processed.md"

_MIN_SIMILARITY = 0.99


def _check_ollama() -> bool:
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if r.status_code != 200:
            return False
        models = [m.get("name", "") for m in r.json().get("models", [])]
        vision_models = [
            "qwen2.5vl", "qwen2.5-vl", "gemma4",
        ]
        return any(
            any(m.startswith(vm) for m in models)
            for vm in vision_models
        )
    except Exception:
        return False


@pytest.mark.skipif(
    not _INPUT_IMAGE.exists(),
    reason="Golden fixture image not found: inputs/transformation_digital/20260527_192417.jpg",
)
@pytest.mark.skipif(
    not _EXPECTED_FILE.exists(),
    reason="Expected output file not found: inputs/transformation_digital/page_1_processed.md",
)
@pytest.mark.skipif(
    not _check_ollama(),
    reason="Ollama not reachable or no vision model available",
)
def test_page1_golden_fixture(tmp_path):
    """Pipeline output must match page_1_processed.md at ≥ 99% similarity."""
    from PIL import Image as PILImage

    from hand2notes.core_models.models import Page, Session, VaultConfig
    from hand2notes.pipeline.orchestrator import run_pipeline

    with PILImage.open(_INPUT_IMAGE) as pil:
        w, h = pil.size

    session = Session(name="golden-page1", notebook="test", topic="test")
    page = Page(
        session_id=session.id,
        source_path=_INPUT_IMAGE,
        sequence=1,
        width_px=w,
        height_px=h,
    )
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    config = VaultConfig(
        vault_root=vault_root,
        folder_template="{{notebook}}/{{topic}}",
        vlm_transcription_enabled=True,
        spell_correction_enabled=False,
    )

    async def _run():
        await run_pipeline(None, session, [page], config)

    asyncio.run(_run())

    notes_files = list(vault_root.rglob("notes.md"))
    assert notes_files, f"No notes.md produced in {vault_root}"

    actual_raw = notes_files[0].read_text(encoding="utf-8")
    # Strip YAML front matter so we compare content only
    actual = re.sub(r"^---\n.*?\n---\n\n?", "", actual_raw, flags=re.DOTALL).strip()
    expected = _EXPECTED_FILE.read_text(encoding="utf-8").strip()

    similarity = difflib.SequenceMatcher(None, expected, actual).ratio()

    if similarity < _MIN_SIMILARITY:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile="expected",
                tofile="actual",
                lineterm="",
            )
        )
        pytest.fail(
            f"Content similarity {similarity:.1%} < {_MIN_SIMILARITY:.0%} threshold.\n"
            f"Diff:\n{diff}"
        )

    # Exact identity check (the gold standard)
    assert actual == expected, (
        f"Content matches at {similarity:.1%} but is not identical.\n"
        "Diff:\n"
        + "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile="expected",
                tofile="actual",
                lineterm="",
            )
        )
    )
