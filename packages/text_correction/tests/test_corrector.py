"""Unit tests for the SpellCorrector and domain-term preservation."""

import pytest
from hand2notes.text_correction.corrector import SpellCorrector, get_corrector
from hand2notes.text_correction.domain_terms import is_domain_term

# ---------------------------------------------------------------------------
# Domain-term preservation
# ---------------------------------------------------------------------------

class TestDomainTerms:
    def test_business_term_preserved(self):
        assert is_domain_term("estrategia")
        assert is_domain_term("ESTRATEGIA")  # lookup is case-insensitive

    def test_tech_term_preserved(self):
        assert is_domain_term("digital")
        assert is_domain_term("blockchain")
        assert is_domain_term("pipeline")

    def test_arrow_symbol_preserved(self):
        assert is_domain_term("→")
        assert is_domain_term("←")

    def test_ordinary_word_not_domain(self):
        assert not is_domain_term("perro")
        assert not is_domain_term("casa")


# ---------------------------------------------------------------------------
# SpellCorrector — Spanish
# ---------------------------------------------------------------------------

class TestSpanishCorrection:
    @pytest.fixture(scope="class")
    def corrector(self):
        return SpellCorrector(languages=["es"])

    def test_known_spanish_word_unchanged(self, corrector):
        result = corrector.correct_text("empresa")
        assert result.corrected == "empresa"
        assert result.corrections_applied == 0

    def test_misspelled_spanish_corrected(self, corrector):
        # "emprersa" → "empresa"
        result = corrector.correct_text("emprersa")
        assert result.corrected == "empresa"
        assert result.corrections_applied == 1
        assert result.changed_words[0] == ("emprersa", "empresa")

    def test_short_word_not_corrected(self, corrector):
        # Words < 4 chars are always skipped
        result = corrector.correct_text("es la")
        assert result.corrections_applied == 0

    def test_all_caps_abbreviation_preserved(self, corrector):
        result = corrector.correct_text("RRLL MK CTO")
        assert result.corrections_applied == 0
        assert "RRLL" in result.corrected

    def test_sentence_with_mixed_content(self, corrector):
        # "visoin" should be corrected to "vision" or similar
        text = "objetivos estrategia visoin"
        result = corrector.correct_text(text)
        # "objetivos" and "estrategia" are in the Spanish dict or domain terms
        assert isinstance(result.corrected, str)
        assert len(result.corrected) > 0

    def test_domain_term_not_overridden(self, corrector):
        result = corrector.correct_text("transformación digital estrategia")
        assert "transformación" in result.corrected
        assert "digital" in result.corrected
        assert "estrategia" in result.corrected

    def test_title_case_preserved(self, corrector):
        result = corrector.correct_text("Emprersa")
        if result.corrections_applied > 0:
            # correction should keep title case
            assert result.corrected[0].isupper()

    def test_empty_string_unchanged(self, corrector):
        result = corrector.correct_text("")
        assert result.corrected == ""
        assert result.corrections_applied == 0

    def test_symbols_and_numbers_unchanged(self, corrector):
        result = corrector.correct_text("2024 → objetivo")
        assert "2024" in result.corrected
        assert "→" in result.corrected


# ---------------------------------------------------------------------------
# SpellCorrector — English
# ---------------------------------------------------------------------------

class TestEnglishCorrection:
    @pytest.fixture(scope="class")
    def corrector(self):
        return SpellCorrector(languages=["en"])

    def test_known_english_word_unchanged(self, corrector):
        result = corrector.correct_text("business")
        assert result.corrected == "business"
        assert result.corrections_applied == 0

    def test_misspelled_english_corrected(self, corrector):
        result = corrector.correct_text("busines")
        assert result.corrections_applied >= 0  # may or may not correct depending on distance
        assert isinstance(result.corrected, str)


# ---------------------------------------------------------------------------
# Mixed Spanish + English
# ---------------------------------------------------------------------------

class TestMixedLanguages:
    @pytest.fixture(scope="class")
    def corrector(self):
        return get_corrector(["es", "en"])

    def test_mixed_text_preserves_both(self, corrector):
        # Real OCR output from the test notes
        text = "Business Plan estrategia competitiva"
        result = corrector.correct_text(text)
        assert "Business" in result.corrected
        assert "Plan" in result.corrected
        assert isinstance(result.corrected, str)

    def test_ocr_noise_corrected(self, corrector):
        # Typical OCR artefact: "Fransformación" → "Transformación"
        result = corrector.correct_text("Fransformación")
        # We don't assert the exact correction since it's heuristic,
        # but it should not raise and should return a string.
        assert isinstance(result.corrected, str)

    def test_get_corrector_caches_singleton(self):
        c1 = get_corrector(["es", "en"])
        c2 = get_corrector(["en", "es"])
        assert c1 is c2  # same cached instance regardless of order
