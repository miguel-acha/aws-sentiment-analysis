"""
test_sentiment_analyzer.py
Tests unitarios para sentiment_analyzer.py usando moto (mock de AWS).
"""

import pytest
import sys
import os
import json
import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch, MagicMock
from sentiment_analyzer import analyze_tracks, SUPPORTED_LANGUAGES


class TestAnalyzeTracks:
    def _mock_comprehend(self, sentiment="POSITIVE", scores=None):
        """Crea un mock del cliente de Comprehend."""
        if scores is None:
            scores = {"Positive": 0.9, "Negative": 0.02, "Neutral": 0.08, "Mixed": 0.0}

        client = MagicMock()
        client.detect_dominant_language.return_value = {
            "Languages": [{"LanguageCode": "en", "Score": 0.99}]
        }
        client.detect_sentiment.return_value = {
            "Sentiment": sentiment,
            "SentimentScore": scores,
        }
        return client

    def _sample_tracks(self):
        return [
            {"track_id": "1", "name": "Happy", "artist": "Pharrell", "text": "Happy Pharrell Williams"},
            {"track_id": "2", "name": "Creep", "artist": "Radiohead", "text": "Creep Radiohead"},
        ]

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_analiza_tracks_correctamente(self, mock_client_fn):
        mock_client_fn.return_value = self._mock_comprehend("POSITIVE")
        tracks = self._sample_tracks()
        results = analyze_tracks(tracks)

        assert len(results) == 2
        assert results[0]["sentiment"] == "POSITIVE"
        assert results[0]["name"] == "Happy"
        assert "scores" in results[0]
        assert "Positive" in results[0]["scores"]

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_fallback_idioma_no_soportado(self, mock_client_fn):
        """Si el idioma detectado no está en SUPPORTED_LANGUAGES → NEUTRAL."""
        client = MagicMock()
        client.detect_dominant_language.return_value = {
            "Languages": [{"LanguageCode": "tl", "Score": 0.95}]  # Tagalog — no soportado
        }
        mock_client_fn.return_value = client

        tracks = [{"track_id": "1", "name": "Test", "artist": "Artist", "text": "Kamusta ka"}]
        results = analyze_tracks(tracks)

        assert results[0]["sentiment"] == "NEUTRAL"
        assert results[0]["scores"]["Neutral"] == 1.0
        # detect_sentiment NO debe llamarse
        client.detect_sentiment.assert_not_called()

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_error_en_comprehend_retorna_neutral(self, mock_client_fn):
        """Si Comprehend falla → fallback a NEUTRAL."""
        from botocore.exceptions import ClientError
        client = MagicMock()
        client.detect_dominant_language.return_value = {
            "Languages": [{"LanguageCode": "en", "Score": 0.99}]
        }
        client.detect_sentiment.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailableException", "Message": "Service unavailable"}},
            "DetectSentiment"
        )
        mock_client_fn.return_value = client

        tracks = [{"track_id": "1", "name": "Test", "artist": "Artist", "text": "Test text"}]
        results = analyze_tracks(tracks)

        assert results[0]["sentiment"] == "NEUTRAL"

    def test_supported_languages_incluye_en_y_es(self):
        assert "en" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_lista_vacia_retorna_vacia(self, mock_client_fn):
        results = analyze_tracks([])
        assert results == []
