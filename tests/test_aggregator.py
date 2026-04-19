"""
test_aggregator.py
Tests unitarios para aggregator.py
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from aggregator import _sentiment_to_score, aggregate, _get_vibe_label

class TestAggregator:
    def test_sentiment_to_score(self):
        # positive - negative
        assert _sentiment_to_score({"Positive": 0.8, "Negative": 0.1}) == 0.7
        assert _sentiment_to_score({"Positive": 0.1, "Negative": 0.9}) == -0.8
        assert _sentiment_to_score({"Positive": 0.4, "Negative": 0.4}) == 0.0
        assert _sentiment_to_score({}) == 0.0

    def test_aggregate_empty_list(self):
        result = aggregate([])
        assert result["total"] == 0
        assert result["dominant"] == "NEUTRAL"
        assert result["weighted_score"] == 0.0

    def test_aggregate_tracks(self):
        tracks = [
            {"sentiment": "POSITIVE", "scores": {"Positive": 0.9, "Negative": 0.0}},
            {"sentiment": "POSITIVE", "scores": {"Positive": 0.8, "Negative": 0.1}},
            {"sentiment": "NEGATIVE", "scores": {"Positive": 0.0, "Negative": 0.9}},
            {"sentiment": "NEUTRAL", "scores": {"Positive": 0.1, "Negative": 0.1}},
        ]
        
        result = aggregate(tracks)
        assert result["total"] == 4
        assert result["dominant"] == "POSITIVE"
        assert result["counts"]["POSITIVE"] == 2
        assert result["counts"]["NEGATIVE"] == 1
        assert result["counts"]["NEUTRAL"] == 1
        assert result["percentages"]["POSITIVE"] == 50.0
        assert result["percentages"]["NEGATIVE"] == 25.0
        assert result["percentages"]["NEUTRAL"] == 25.0
        
        # weighted score:
        # T1 = 0.9
        # T2 = 0.7
        # T3 = -0.9
        # T4 = 0.0
        # total = 0.7
        # 0.7 / 4 = 0.175
        assert result["weighted_score"] == pytest.approx(0.175)

    def test_aggregate_mixed_sentiment(self):
        # MIXED debe mapearse al mayor score entre Positive, Negative, Neutral
        tracks = [
            {"sentiment": "MIXED", "scores": {"Positive": 0.2, "Negative": 0.7, "Neutral": 0.1}}
        ]
        result = aggregate(tracks)
        # Should be mapped to NEGATIVE
        assert result["counts"]["NEGATIVE"] == 1
        assert result["dominant"] == "NEGATIVE"

    def test_get_vibe_label(self):
        assert _get_vibe_label(0.6) == "🌟 Muy Positiva"
        assert _get_vibe_label(0.3) == "😊 Positiva"
        assert _get_vibe_label(0.0) == "😐 Neutral"
        assert _get_vibe_label(-0.3) == "😔 Melancólica"
        assert _get_vibe_label(-0.8) == "😢 Muy Negativa"
