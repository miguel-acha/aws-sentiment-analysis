"""
spotify_client.py
-----------------
Autentica con Spotify vía Client Credentials Flow y extrae
las canciones de una playlist pública.

Retorna:
    Lista de dicts con { track_id, name, artist, text }
    donde `text` = "nombre + artista" (MVP — sin letras reales)
"""

import re
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


def _extract_playlist_id(playlist_url: str) -> str:
    """Extrae el playlist_id de una URL o ID directo de Spotify."""
    # Si ya es un ID puro (sin slash ni http)
    if "/" not in playlist_url and "spotify:" not in playlist_url:
        return playlist_url

    # URL formato: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
    match = re.search(r"playlist/([A-Za-z0-9]+)", playlist_url)
    if match:
        return match.group(1)

    # URI formato: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
    match = re.search(r"spotify:playlist:([A-Za-z0-9]+)", playlist_url)
    if match:
        return match.group(1)

    raise ValueError(f"No se pudo extraer el playlist_id de: {playlist_url}")


def get_playlist_info(sp: spotipy.Spotify, playlist_id: str) -> dict:
    """Retorna metadata básica de la playlist (nombre, imagen, owner)."""
    data = sp.playlist(playlist_id, fields="name,description,owner,images,tracks(total)")
    return {
        "name": data.get("name", "Playlist"),
        "description": data.get("description", ""),
        "owner": data.get("owner", {}).get("display_name", "Unknown"),
        "image_url": data["images"][0]["url"] if data.get("images") else None,
        "total_tracks": data["tracks"]["total"],
    }


def get_playlist_tracks(playlist_url: str, max_tracks: int = 100) -> tuple[dict, list[dict]]:
    """
    Autentica y extrae las canciones de una playlist de Spotify.

    Args:
        playlist_url: URL completa o ID de la playlist
        max_tracks: Máximo de canciones a procesar (default 100 para evitar costos altos en Comprehend)

    Returns:
        Tuple (playlist_info, tracks)
        tracks: lista de dicts { track_id, name, artist, album, text, duration_ms, popularity }
    """
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Faltan SPOTIFY_CLIENT_ID y/o SPOTIFY_CLIENT_SECRET en las variables de entorno"
        )

    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    playlist_id = _extract_playlist_id(playlist_url)

    # Obtener info de la playlist
    playlist_info = get_playlist_info(sp, playlist_id)

    # Paginar y extraer tracks
    tracks = []
    offset = 0
    limit = 50  # Máximo permitido por la API de Spotify

    while len(tracks) < max_tracks:
        results = sp.playlist_tracks(
            playlist_id,
            offset=offset,
            limit=limit,
            fields="items(track(id,name,artists,album,duration_ms,popularity)),next",
        )

        items = results.get("items", [])
        if not items:
            break

        for item in items:
            track = item.get("track")
            if not track or not track.get("id"):
                continue  # Saltar tracks locales o nulos

            artist = track["artists"][0]["name"] if track.get("artists") else "Unknown Artist"
            name = track.get("name", "Unknown")

            tracks.append(
                {
                    "track_id": track["id"],
                    "name": name,
                    "artist": artist,
                    "album": track.get("album", {}).get("name", ""),
                    # MVP: usamos nombre + artista como texto para Comprehend
                    # Fase 2: reemplazar con letras reales de Genius API
                    "text": f"{name} {artist}",
                    "duration_ms": track.get("duration_ms", 0),
                    "popularity": track.get("popularity", 0),
                }
            )

            if len(tracks) >= max_tracks:
                break

        if not results.get("next"):
            break
        offset += limit

    return playlist_info, tracks


if __name__ == "__main__":
    # Test rápido
    from dotenv import load_dotenv
    load_dotenv()

    test_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    info, tracks = get_playlist_tracks(test_url, max_tracks=5)
    print(f"Playlist: {info['name']} ({info['total_tracks']} canciones)")
    for t in tracks:
        print(f"  - {t['name']} | {t['artist']}")
