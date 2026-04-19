"""
test_chart_generator.py
Tests unitarios limitados para chart_generator.py para asegurar que matplotlib funciona sin display.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chart_generator import render_gauge, render_donut, generate_report_png

class TestChartGenerator:
    def test_render_gauge(self):
        img_bytes = render_gauge(0.5, "Positiva")
        assert img_bytes is not None
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0

    def test_render_donut(self):
        img_bytes = render_donut({"POSITIVE": 50, "NEGATIVE": 50}, {"POSITIVE": 1, "NEGATIVE": 1})
        assert img_bytes is not None
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0

    def test_generate_report_png(self):
        analyzed_tracks = []
        summary = {
            "total": 2,
            "weighted_score": 0.5,
            "vibe_label": "Positiva",
            "percentages": {"POSITIVE": 50, "NEGATIVE": 50},
            "counts": {"POSITIVE": 1, "NEGATIVE": 1}
        }
        playlist_info = {"name": "Test Playlist"}
        
        img_bytes = generate_report_png(analyzed_tracks, summary, playlist_info)
        assert img_bytes is not None
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0
