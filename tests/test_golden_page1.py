"""Golden fixture test for page_1: 20260527_192417.jpg → page_1_processed.md.

This test is the primary quality gate for the full pipeline on the first
annotated golden example. It runs the complete pipeline end-to-end and
compares the produced content against the human-curated reference.

Quality metric: accent/plural-insensitive WORD RECALL — the fraction of the
reference's words that the pipeline genuinely transcribed. We deliberately do
NOT use character-identical matching: the reference is a hand-curated ideal
(with specific table/spatial formatting), while a local VLM produces faithful
content in a slightly different structure. Word recall measures real
transcription accuracy without penalising formatting choices.

Pass threshold: ≥ 80% word recall. On the current pipeline (Qwen2.5-VL) page 1
genuinely scores ~87%. (Historical note: a previous version appeared to score
100%, but only because the gemma4 fallback prompt embedded this page's answer
as a "format example" — the answer was leaked into the prompt, not transcribed.
That leak has been removed; this test now measures genuine capability.)

Requires Ollama to be running with at least one supported VLM:
  - qwen2.5vl:7b  (preferred)
  - gemma4:e4b    (fallback)

Skip conditions:
  - Input image not present in inputs/transformation_digital/
  - Ollama not reachable
"""

import asyncio
import collections
import re
import unicodedata
from pathlib import Path

import pytest

_INPUTS_DIR = Path(__file__).parent.parent / "inputs" / "transformation_digital"
_INPUT_IMAGE = _INPUTS_DIR / "20260527_192417.jpg"
_EXPECTED_FILE = _INPUTS_DIR / "page_1_processed.md"

_MIN_WORD_RECALL = 0.80


def _normalised_tokens(text: str) -> list[str]:
    """Lower-case, strip accents and Markdown punctuation, drop a trailing plural -s."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[#|>*\-]", " ", text)
    return [w.rstrip("s") for w in re.findall(r"[a-z0-9]+", text) if len(w) > 1]


def _word_recall(reference: str, actual: str) -> float:
    ref = collections.Counter(_normalised_tokens(reference))
    act = collections.Counter(_normalised_tokens(actual))
    if not ref:
        return 0.0
    captured = sum((ref & act).values())
    return captured / sum(ref.values())


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
    """Pipeline output must capture ≥ 80% of the reference's words (word recall)."""
    from hand2notes.core_models.models import Page, Session, VaultConfig
    from PIL import Image as PILImage

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

    recall = _word_recall(expected, actual)

    if recall < _MIN_WORD_RECALL:
        ref_tokens = set(_normalised_tokens(expected))
        act_tokens = set(_normalised_tokens(actual))
        missing = sorted(ref_tokens - act_tokens)
        pytest.fail(
            f"Word recall {recall:.1%} < {_MIN_WORD_RECALL:.0%} threshold.\n"
            f"Reference words not transcribed: {missing}\n\n"
            f"--- actual output ---\n{actual}"
        )
