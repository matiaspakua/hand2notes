"""Shared pytest fixtures/configuration for hand2notes tests."""

import os


def pytest_configure(config):  # noqa: ARG001
    # Never let the on-disk VLM transcription cache mask a regression: tests must
    # exercise the live pipeline (or be skipped when Ollama is unavailable), not a
    # stale cached transcription from a previous code version.
    os.environ["HAND2NOTES_DISABLE_VLM_CACHE"] = "1"
