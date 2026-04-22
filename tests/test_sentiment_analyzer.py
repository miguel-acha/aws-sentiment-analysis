"""
test_sentiment_analyzer.py
Tests unitarios para sentiment_analyzer.py usando mocks.
"""

import os
import sys
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sentiment_analyzer import SUPPORTED_LANGUAGES, analyze_tracks


class TestAnalyzeTracks:
    def _mock_comprehend(self, sentiment="POSITIVE", scores=None):
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

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_analiza_tracks_correctamente(self, mock_client_fn):
        mock_client_fn.return_value = self._mock_comprehend("POSITIVE")

        tracks = [
            {"track_id": "1", "name": "Happy", "artist": "Pharrell", "text": "Happy Pharrell Williams"},
            {
                "track_id": "2",
                "name": "Fiesta",
                "artist": "Artist",
                "text": "[Chorus]\nPerreo duro en el jangueo\nPerreo duro en el jangueo",
            },
        ]
        results = analyze_tracks(tracks)

        assert len(results) == 2
        assert "scores" in results[0]
        assert "preprocessing_stats" in results[0]

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_envia_texto_preprocesado_a_comprehend(self, mock_client_fn):
        client = self._mock_comprehend("POSITIVE")
        mock_client_fn.return_value = client

        tracks = [
            {
                "track_id": "1",
                "name": "Reggaeton Test",
                "artist": "Artist",
                "text": "[Intro]\nyeah yeah\nBellaqueo y perreo en el jangueo con flow",
            }
        ]
        analyze_tracks(tracks)

        detect_language_text = client.detect_dominant_language.call_args.kwargs["Text"]
        detect_sentiment_text = client.detect_sentiment.call_args.kwargs["Text"]

        assert "bellaqueo" not in detect_sentiment_text.lower()
        assert "deseo seduccion fiesta" in detect_sentiment_text.lower()
        assert "baile sensual fiesta" in detect_sentiment_text.lower()
        assert detect_language_text == detect_sentiment_text[:300]

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_fallback_idioma_no_soportado(self, mock_client_fn):
        client = MagicMock()
        client.detect_dominant_language.return_value = {
            "Languages": [{"LanguageCode": "tl", "Score": 0.95}]
        }
        mock_client_fn.return_value = client

        tracks = [{"track_id": "1", "name": "Test", "artist": "Artist", "text": "Kamusta ka"}]
        results = analyze_tracks(tracks)

        assert results[0]["sentiment"] == "NEUTRAL"
        assert results[0]["scores"]["Neutral"] == 1.0
        client.detect_sentiment.assert_not_called()

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_error_en_comprehend_retorna_neutral(self, mock_client_fn):
        client = MagicMock()
        client.detect_dominant_language.return_value = {
            "Languages": [{"LanguageCode": "en", "Score": 0.99}]
        }
        client.detect_sentiment.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailableException", "Message": "Service unavailable"}},
            "DetectSentiment",
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
        assert analyze_tracks([]) == []

    @patch("sentiment_analyzer._get_comprehend_client")
    def test_hybrid_uplift_para_track_bailable(self, mock_client_fn):
        client = self._mock_comprehend(
            sentiment="NEGATIVE",
            scores={"Positive": 0.12, "Negative": 0.58, "Neutral": 0.22, "Mixed": 0.08},
        )
        mock_client_fn.return_value = client

        tracks = [
            {
                "track_id": "1",
                "name": "NUEVAYoL",
                "artist": "Bad Bunny",
                "text": "To' el mundo turnt up, perreando con la shawty y mucho flow",
                "audio_features": {
                    "danceability": 0.91,
                    "energy": 0.84,
                    "valence": 0.68,
                    "tempo": 111.0,
                    "speechiness": 0.07,
                    "acousticness": 0.10,
                    "instrumentalness": 0.0,
                    "mode": 1,
                },
            }
        ]

        results = analyze_tracks(tracks)

        assert results[0]["lyric_sentiment"] == "NEGATIVE"
        assert results[0]["audio_vibe_score"] > 0
        assert results[0]["vibe_score"] > 0
        assert results[0]["sentiment"] == "POSITIVE"
