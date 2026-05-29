"""Unit tests for Qwen2.5-VL post-processing and the transcription cache.

All pure-logic — no Ollama required — so they run in milliseconds and guard the
fragile bits: repetition collapse, fence handling, image downscale, and caching.
"""

import io

import pytest
from PIL import Image

from hand2notes.ocr import qwen_vl_transcriber as qt


# ── repetition collapse ──────────────────────────────────────────────────────

def test_collapse_repeated_block():
    text = "Plan de IT\n-->\nPlan de\n" * 6
    out = qt._collapse_repetitions(text.strip())
    assert out.count("Plan de IT") == 1


def test_collapse_keeps_distinct_lines():
    text = "uno\ndos\ntres"
    assert qt._collapse_repetitions(text) == text


def test_collapse_drops_adjacent_duplicate_lines():
    assert qt._collapse_repetitions("a\na\nb") == "a\nb"


# ── outer fence unwrap ───────────────────────────────────────────────────────

def test_unwrap_markdown_wrapper():
    wrapped = "```markdown\n# Title\n\ntext\n```"
    assert qt._unwrap_outer_fence(wrapped) == "# Title\n\ntext"


def test_unwrap_preserves_inner_mermaid():
    wrapped = "```markdown\n# T\n\n```mermaid\nflowchart TD\n  A-->B\n```\n```"
    out = qt._unwrap_outer_fence(wrapped)
    assert out.startswith("# T")
    assert "```mermaid" in out


def test_unwrap_leaves_plain_text():
    assert qt._unwrap_outer_fence("# Title\ntext") == "# Title\ntext"


# ── dangling fence ───────────────────────────────────────────────────────────

def test_close_dangling_fence_adds_close():
    assert qt._close_dangling_fence("```mermaid\nflowchart TD").endswith("```")


def test_close_dangling_fence_noop_when_balanced():
    balanced = "```mermaid\nflowchart TD\n```"
    assert qt._close_dangling_fence(balanced) == balanced


# ── full post-process ────────────────────────────────────────────────────────

def test_post_process_arrow_and_numbered():
    out = qt._post_process("Empresa → estrategia\n1. primero")
    assert "-->" in out and "→" not in out
    assert "1 . primero" in out


def test_post_process_discards_runaway_mermaid_keeps_text():
    body = "flowchart TD\n" + "".join(f"    A -->|x| B{i}[ICTA]\n" for i in range(40))
    out = qt._post_process(f"# Heading\n\n```mermaid\n{body}```\n\ntail")
    assert "```mermaid" not in out
    assert "# Heading" in out and "tail" in out


# ── image downscale guard ────────────────────────────────────────────────────

def test_encode_image_downscales_oversized(tmp_path):
    big = tmp_path / "big.jpg"
    Image.new("RGB", (4000, 3000), "white").save(big, "JPEG")
    b64 = qt._encode_image(big)
    import base64
    decoded = Image.open(io.BytesIO(base64.b64decode(b64)))
    assert max(decoded.size) <= qt._MAX_IMAGE_EDGE


def test_encode_image_keeps_small(tmp_path):
    small = tmp_path / "small.jpg"
    Image.new("RGB", (800, 600), "white").save(small, "JPEG")
    import base64
    decoded = Image.open(io.BytesIO(base64.b64decode(qt._encode_image(small))))
    assert decoded.size == (800, 600)


# ── cache ────────────────────────────────────────────────────────────────────

@pytest.fixture
def _cache_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HAND2NOTES_VLM_CACHE", str(tmp_path / "cache"))
    monkeypatch.delenv("HAND2NOTES_DISABLE_VLM_CACHE", raising=False)


def test_cache_round_trip(_cache_env):
    key = qt._cache_key("image-bytes-b64", include_diagrams=True)
    assert qt._cache_get(key) is None
    qt._cache_put(key, "# cached note")
    assert qt._cache_get(key) == "# cached note"


def test_cache_key_depends_on_inputs(_cache_env):
    k1 = qt._cache_key("imgA", include_diagrams=True)
    k2 = qt._cache_key("imgB", include_diagrams=True)
    k3 = qt._cache_key("imgA", include_diagrams=False)
    assert k1 != k2 and k1 != k3


def test_cache_disabled_via_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HAND2NOTES_VLM_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("HAND2NOTES_DISABLE_VLM_CACHE", "1")
    key = qt._cache_key("x", include_diagrams=True)
    qt._cache_put(key, "value")
    assert qt._cache_get(key) is None
