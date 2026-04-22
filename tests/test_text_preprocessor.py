"""
test_text_preprocessor.py
Tests unitarios para el preprocesador de letras.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from text_preprocessor import preprocess_lyrics_for_comprehend


class TestTextPreprocessor:
    def test_reduce_headers_adlibs_and_duplicate_chorus(self):
        lyrics = """
        [Intro]
        yeah yeah yeah
        Perreo hasta abajo
        [Chorus]
        Perreo hasta abajo
        Perreo hasta abajo
        Perreo hasta abajo
        """

        result = preprocess_lyrics_for_comprehend(lyrics)

        assert "yeah yeah yeah" not in result["text"].lower()
        assert "[chorus]" not in result["text"].lower()
        assert result["text"].lower().count("baile sensual fiesta") <= 2
        assert result["stats"]["duplicate_lines_trimmed"] >= 1

    def test_expand_spanish_urban_slang(self):
        lyrics = "Bellaqueo y perreo en el jangueo con mucho flow."
        result = preprocess_lyrics_for_comprehend(lyrics)
        lowered = result["text"].lower()

        assert "deseo seduccion fiesta" in lowered
        assert "baile sensual fiesta" in lowered
        assert "fiesta diversion amigos" in lowered
        assert "estilo confianza" in lowered
        assert result["stats"]["slang_hits"] >= 4

    def test_expand_english_slang_and_contractions(self):
        lyrics = "We lit, shawty vibin and I'm finna flex."
        result = preprocess_lyrics_for_comprehend(lyrics)
        lowered = result["text"].lower()

        assert "exciting fun party" in lowered
        assert "desired person" in lowered
        assert "good mood enjoying" in lowered
        assert "about to" in lowered
        assert "confidence success" in lowered

    def test_keep_mixed_spanish_english_party_context_semantic(self):
        lyrics = "To' el mundo turnt up, perreando con la shawty y mucho flow."
        result = preprocess_lyrics_for_comprehend(lyrics)
        lowered = result["text"].lower()

        assert "todo el mundo" in lowered
        assert "party celebration energy" in lowered
        assert "baile sensual fiesta" in lowered
        assert "desired person" in lowered
        assert "estilo confianza" in lowered

    def test_preserve_real_violence_as_negative_context(self):
        lyrics = "Opps outside, we smoke them and the glock ready for the drive by."
        result = preprocess_lyrics_for_comprehend(lyrics)
        lowered = result["text"].lower()

        assert "enemy conflict" in lowered
        assert "threat violence" in lowered
        assert "weapon violence" in lowered
        assert "violence attack" in lowered

    def test_fallback_to_original_when_too_short(self):
        lyrics = "go"
        result = preprocess_lyrics_for_comprehend(lyrics)

        assert result["text"] == "go"
        assert result["stats"]["used_fallback"] is True
