"""
test_spotify_client.py
Tests unitarios para spotify_client.py con mocks del cliente HTTP.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spotify_client import _extract_playlist_id, _get_audio_features_map, get_playlist_tracks


class TestExtractPlaylistId:
    def test_url_completa(self):
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        assert _extract_playlist_id(url) == "37i9dQZF1DXcBWIGoYBM5M"

    def test_url_con_query_params(self):
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc123"
        assert _extract_playlist_id(url) == "37i9dQZF1DXcBWIGoYBM5M"

    def test_uri_spotify(self):
        uri = "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
        assert _extract_playlist_id(uri) == "37i9dQZF1DXcBWIGoYBM5M"

    def test_id_directo(self):
        pid = "37i9dQZF1DXcBWIGoYBM5M"
        assert _extract_playlist_id(pid) == "37i9dQZF1DXcBWIGoYBM5M"

    def test_url_invalida(self):
        with pytest.raises(ValueError):
            _extract_playlist_id("https://open.spotify.com/album/abc123")


class TestSpotifyClient:
    @patch("spotify_client._spotify_get")
    def test_get_audio_features_map(self, mock_spotify_get):
        mock_spotify_get.return_value = {
            "audio_features": [
                {
                    "id": "track-1",
                    "danceability": 0.91,
                    "energy": 0.82,
                    "valence": 0.74,
                    "tempo": 110.0,
                    "speechiness": 0.08,
                    "acousticness": 0.12,
                    "instrumentalness": 0.0,
                    "liveness": 0.18,
                    "mode": 1,
                }
            ]
        }

        feature_map = _get_audio_features_map("token", ["track-1"])

        assert feature_map["track-1"]["danceability"] == 0.91
        assert feature_map["track-1"]["valence"] == 0.74

    @patch("spotify_client.enrich_tracks_with_lyrics")
    @patch("spotify_client._get_audio_features_map")
    @patch("spotify_client.get_playlist_info")
    @patch("spotify_client._spotify_get")
    def test_get_playlist_tracks_incluye_audio_features(
        self,
        mock_spotify_get,
        mock_get_playlist_info,
        mock_get_audio_features_map,
        mock_enrich_tracks,
    ):
        mock_get_playlist_info.return_value = {
            "name": "Test Playlist",
            "owner": "Tester",
            "total_tracks": 1,
            "description": "",
            "image_url": None,
        }
        mock_spotify_get.return_value = {
            "items": [
                {
                    "item": {
                        "id": "track-1",
                        "name": "DtMF",
                        "artists": [{"id": "artist-1", "name": "Bad Bunny"}],
                        "album": {"name": "Album"},
                        "duration_ms": 222000,
                        "external_ids": {"isrc": "USUM12345678"},
                    }
                }
            ],
            "next": None,
        }
        mock_get_audio_features_map.return_value = {
            "track-1": {"danceability": 0.9, "energy": 0.8, "valence": 0.6}
        }
        mock_enrich_tracks.side_effect = lambda tracks: tracks

        info, tracks = get_playlist_tracks(
            "37i9dQZF1DXcBWIGoYBM5M", max_tracks=1, access_token="user-token"
        )

        assert info["name"] == "Test Playlist"
        assert len(tracks) == 1
        assert tracks[0]["name"] == "DtMF"
        assert tracks[0]["audio_features"]["danceability"] == 0.9
        assert tracks[0]["isrc"] == "USUM12345678"

    def test_sin_credenciales_lanza_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SPOTIFY_CLIENT_ID"):
                get_playlist_tracks("37i9dQZF1DXcBWIGoYBM5M")
