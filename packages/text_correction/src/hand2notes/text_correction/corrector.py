"""Conservative spell-corrector for post-OCR handwritten text (Spanish + English).

Design principles:
- Conservative: only correct when a high-confidence match exists.
- Non-destructive: original text is preserved alongside the corrected version.
- Domain-aware: business/tech terms are never altered (see domain_terms.py).
- Abbreviation-safe: ALL-CAPS words, words with digits, and short tokens are skipped.
- Fast: both language models are loaded once and cached at module level.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from functools import cached_property
from typing import Sequence

from .domain_terms import is_domain_term

# Maximum edit-distance for a correction to be accepted (Damerau-Levenshtein).
_MAX_EDIT_DISTANCE = 2
# Minimum word length to attempt correction (avoids garbling short tokens).
_MIN_WORD_LEN = 4
# Thread-safe singleton lock.
_lock = threading.Lock()
_corrector_cache: dict[tuple[str, ...], "SpellCorrector"] = {}


@dataclass
class CorrectionResult:
    original: str
    corrected: str
    corrections_applied: int
    changed_words: list[tuple[str, str]] = field(default_factory=list)  # (original, replacement)


class SpellCorrector:
    """Spell-corrects text blocks for the given language codes.

    Supported language codes: 'es' (Spanish), 'en' (English).
    Load once per language combination; subsequent calls are fast.
    """

    def __init__(self, languages: Sequence[str] = ("es", "en")) -> None:
        self._languages = tuple(dict.fromkeys(lang.lower() for lang in languages))

    @cached_property
    def _checkers(self) -> list:
        """Lazily load one SpellChecker per language, cached on first use."""
        from spellchecker import SpellChecker
        checkers = []
        for lang in self._languages:
            try:
                checkers.append(SpellChecker(language=lang, distance=_MAX_EDIT_DISTANCE))
            except Exception:
                # Language not available; skip silently
                pass
        return checkers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def correct_text(self, text: str) -> CorrectionResult:
        """Return a CorrectionResult with corrected text and metadata."""
        if not text or not text.strip():
            return CorrectionResult(original=text, corrected=text, corrections_applied=0)

        tokens = _tokenize(text)
        corrected_tokens: list[str] = []
        changed: list[tuple[str, str]] = []

        for token in tokens:
            replacement = self._maybe_correct_word(token)
            corrected_tokens.append(replacement)
            if replacement != token:
                changed.append((token, replacement))

        corrected = _reconstruct(tokens, corrected_tokens, text)
        return CorrectionResult(
            original=text,
            corrected=corrected,
            corrections_applied=len(changed),
            changed_words=changed,
        )

    def is_known(self, word: str) -> bool:
        """Return True if the word is in any of the loaded dictionaries."""
        w = word.lower()
        return any(not checker.unknown([w]) for checker in self._checkers)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_correct_word(self, word: str) -> str:
        """Return a corrected word, or the original if no safe correction exists."""
        if _should_skip(word):
            return word
        if is_domain_term(word):
            return word
        # Check if it's already known in any language
        word_lower = word.lower()
        for checker in self._checkers:
            if not checker.unknown([word_lower]):
                return word  # correct already — preserve original casing
        # Try to find a correction
        for checker in self._checkers:
            suggestion = checker.correction(word_lower)
            if suggestion and suggestion != word_lower:
                # Apply correction preserving original capitalisation pattern
                return _apply_case(word, suggestion)
        return word


# ──────────────────────────────────────────────────────────────────────────────
# Tokenisation helpers
# ──────────────────────────────────────────────────────────────────────────────

# Matches a contiguous run of alphabetic characters (including accented letters).
_WORD_RE = re.compile(r"[A-Za-záéíóúüñÁÉÍÓÚÜÑàèìòùÀÈÌÒÙ]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Split text into word and non-word tokens, preserving all characters."""
    tokens: list[str] = []
    last = 0
    for m in _WORD_RE.finditer(text):
        if m.start() > last:
            tokens.append(text[last : m.start()])  # non-word gap
        tokens.append(m.group())
        last = m.end()
    if last < len(text):
        tokens.append(text[last:])
    return tokens


def _reconstruct(original_tokens: list[str], new_tokens: list[str], original_text: str) -> str:
    """Rebuild text from token lists. Falls back to original on any mismatch."""
    if len(original_tokens) != len(new_tokens):
        return original_text
    return "".join(new_tokens)


def _should_skip(word: str) -> bool:
    """Return True for tokens that must never be spell-corrected."""
    if len(word) < _MIN_WORD_LEN:
        return True
    if word.isupper():  # abbreviation
        return True
    if any(ch.isdigit() for ch in word):  # contains number
        return True
    if not word.isalpha():  # has symbols
        return True
    return False


def _apply_case(original: str, suggestion: str) -> str:
    """Apply the capitalisation pattern of `original` to `suggestion`."""
    if original.isupper():
        return suggestion.upper()
    if original.istitle():
        return suggestion.capitalize()
    if original[0].isupper():
        return suggestion[0].upper() + suggestion[1:]
    return suggestion


# ──────────────────────────────────────────────────────────────────────────────
# Module-level convenience factory (singleton per language set)
# ──────────────────────────────────────────────────────────────────────────────

def get_corrector(languages: Sequence[str] = ("es", "en")) -> SpellCorrector:
    """Return a cached SpellCorrector for the given language combination."""
    key = tuple(sorted(set(lang.lower() for lang in languages)))
    with _lock:
        if key not in _corrector_cache:
            _corrector_cache[key] = SpellCorrector(languages=key)
        return _corrector_cache[key]
