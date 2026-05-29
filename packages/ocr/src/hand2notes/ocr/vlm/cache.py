"""On-disk transcription cache, keyed by image bytes + prompts + options.

A repeated run of the same image returns in milliseconds instead of re-invoking the
VLM. Disable with HAND2NOTES_DISABLE_VLM_CACHE=1 (read at call time so tests can toggle
it). Override the location with HAND2NOTES_VLM_CACHE.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

# Bump when prompts/options/post-processing change so stale entries are ignored.
CACHE_VERSION = "v3-1280-2pass-modular"


def cache_dir() -> Path:
    return Path(
        os.environ.get("HAND2NOTES_VLM_CACHE", Path(tempfile.gettempdir()) / "hand2notes_vlm_cache")
    )


def cache_enabled() -> bool:
    return os.environ.get("HAND2NOTES_DISABLE_VLM_CACHE", "") not in ("1", "true", "True")


def cache_key(*materials: str) -> str:
    """Stable hash of CACHE_VERSION plus all key materials (prompts, options, image)."""
    h = hashlib.sha256()
    h.update(CACHE_VERSION.encode("utf-8"))
    for part in materials:
        h.update(b"\x00")
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def cache_get(key: str) -> str | None:
    if not cache_enabled():
        return None
    try:
        return (cache_dir() / f"{key}.md").read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None


def cache_put(key: str, value: str) -> None:
    if not cache_enabled():
        return
    try:
        cache_dir().mkdir(parents=True, exist_ok=True)
        (cache_dir() / f"{key}.md").write_text(value, encoding="utf-8")
    except OSError as exc:  # noqa: BLE001 — caching is best-effort
        log.debug("VLM cache write failed: %s", exc)
