"""
test_spotify_client.py
Tests unitarios para spotify_client.py usando mocks de spotipy.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from unittest.mock import patch, MagicMock
from spotify_client import _extract_playlist_id, get_playlist_tracks


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


class TestGetPlaylistTracks:
    def _make_mock_sp(self):
        """Crea un mock de Spotify con 3 canciones."""
        sp = MagicMock()
        sp.playlist.return_value = {
            "name": "Test Playlist",
            "description": "Test",
            "owner": {"display_name": "Test User"},
            "images": [{"url": "https://example.com/img.jpg"}],
            "tracks": {"total": 3},
        }
        sp.playlist_tracks.return_value = {
            "items": [
                {"track": {"id": "1", "name": "Happy", "artists": [{"name": "Pharrell Williams"}],
                            "album": {"name": "GIRL"}, "duration_ms": 233000, "popularity": 80}},
                {"track": {"id": "2", "name": "Creep", "artists": [{"name": "Radiohead"}],
                            "album": {"name": "Pablo Honey"}, "duration_ms": 238000, "popularity": 75}},
                {"track": None},  # Track nulo — debe ignorarse
            ],
            "next": None,
        }
        return sp

    @patch("spotify_client.spotipy.Spotify")
    @patch("spotify_client.SpotifyClientCredentials")
    def test_retorna_tracks_correctamente(self, mock_creds, mock_spotify):
        mock_spotify.return_value = self._make_mock_sp()

        with patch.dict(os.environ, {
            "SPOTIFY_CLIENT_ID": "test_id",
            "SPOTIFY_CLIENT_SECRET": "test_secret",
        }):
            info, tracks = get_playlist_tracks("37i9dQZF1DXcBWIGoYBM5M")

        assert len(tracks) == 2  # El track None debe ignorarse
        assert tracks[0]["name"] == "Happy"
        assert tracks[0]["artist"] == "Pharrell Williams"
        assert tracks[0]["text"] == "Happy Pharrell Williams"
        assert tracks[1]["name"] == "Creep"

    @patch("spotify_client.spotipy.Spotify")
    @patch("spotify_client.SpotifyClientCredentials")
    def test_retorna_playlist_info(self, mock_creds, mock_spotify):
        mock_spotify.return_value = self._make_mock_sp()

        with patch.dict(os.environ, {
            "SPOTIFY_CLIENT_ID": "test_id",
            "SPOTIFY_CLIENT_SECRET": "test_secret",
        }):
            info, _ = get_playlist_tracks("37i9dQZF1DXcBWIGoYBM5M")

        assert info["name"] == "Test Playlist"
        assert info["owner"] == "Test User"
        assert info["total_tracks"] == 3

    def test_sin_credenciales_lanza_error(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SPOTIFY_CLIENT_ID", None)
            os.environ.pop("SPOTIFY_CLIENT_SECRET", None)
            with pytest.raises(ValueError, match="SPOTIFY_CLIENT_ID"):
                get_playlist_tracks("37i9dQZF1DXcBWIGoYBM5M")
