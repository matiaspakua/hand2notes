"""Internal helpers for the Qwen2.5-VL transcriber.

Split out of ``qwen_vl_transcriber`` to keep each concern small and independently
testable (Principle IV — Modular & Swappable):

- ``prompts``      — the text-pass and diagram-pass prompt strings
- ``mermaid``      — Mermaid sanitisation / fence handling (the VLM-garbage safety net)
- ``text_cleanup`` — post-processing of raw VLM Markdown (arrows, repetition, mermaid)
- ``cache``        — on-disk transcription cache keyed by image + prompts + options
"""
