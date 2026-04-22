"""
test_aggregator.py
Tests unitarios para aggregator.py
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aggregator import _get_vibe_label, _sentiment_to_score, aggregate


class TestAggregator:
    def test_sentiment_to_score_usa_vibe_score_si_existe(self):
        assert _sentiment_to_score({"vibe_score": 0.42, "scores": {"Positive": 0.1, "Negative": 0.7}}) == 0.42
        assert _sentiment_to_score({"Positive": 0.8, "Negative": 0.1}) == 0.7

    def test_aggregate_empty_list(self):
        result = aggregate([])
        assert result["total"] == 0
        assert result["dominant"] == "NEUTRAL"
        assert result["weighted_score"] == 0.0

    def test_aggregate_tracks_uses_hybrid_sentiment(self):
        tracks = [
            {"sentiment": "POSITIVE", "vibe_score": 0.62},
            {"sentiment": "POSITIVE", "vibe_score": 0.38},
            {"sentiment": "NEGATIVE", "vibe_score": -0.44},
            {"sentiment": "NEUTRAL", "vibe_score": 0.02},
        ]

        result = aggregate(tracks)

        assert result["total"] == 4
        assert result["dominant"] == "POSITIVE"
        assert result["counts"]["POSITIVE"] == 2
        assert result["counts"]["NEGATIVE"] == 1
        assert result["counts"]["NEUTRAL"] == 1
        assert result["percentages"]["POSITIVE"] == 50.0
        assert result["weighted_score"] == pytest.approx(0.2538)

    def test_mixed_can_be_dominant_if_count_wins(self):
        tracks = [
            {"sentiment": "MIXED", "vibe_score": 0.03},
            {"sentiment": "MIXED", "vibe_score": -0.02},
            {"sentiment": "NEGATIVE", "vibe_score": -0.4},
        ]

        result = aggregate(tracks)

        assert result["counts"]["MIXED"] == 2
        assert result["dominant"] == "MIXED"

    def test_get_vibe_label(self):
        assert _get_vibe_label(0.6) == "Euforico"
        assert _get_vibe_label(0.35) == "Radiante"
        assert _get_vibe_label(0.18) == "Fiestero"
        assert _get_vibe_label(0.0) == "Equilibrado"
        assert _get_vibe_label(-0.2) == "Melancolico"
        assert _get_vibe_label(-0.4) == "Introspectivo"
        assert _get_vibe_label(-0.8) == "Sombrio"
