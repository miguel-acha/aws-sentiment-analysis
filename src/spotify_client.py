"""
spotify_client.py
-----------------
Autentica con Spotify y extrae las canciones de una playlist.

Actualizado para la API moderna:
- Usa GET /playlists/{id}/items
- Acepta access_token de usuario (PKCE)
- Fallback a Client Credentials si no se pasa token
- Enriquece los tracks con audio features y letras reales
"""

import base64
import os
import re

import requests

from musixmatch_client import enrich_tracks_with_lyrics


SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


def _extract_playlist_id(playlist_url: str) -> str:
    if "/" not in playlist_url and "spotify:" not in playlist_url:
        return playlist_url

    match = re.search(r"playlist/([A-Za-z0-9]+)", playlist_url)
    if match:
        return match.group(1)

    match = re.search(r"spotify:playlist:([A-Za-z0-9]+)", playlist_url)
    if match:
        return match.group(1)

    raise ValueError(f"No se pudo extraer el playlist_id de: {playlist_url}")


def _get_client_credentials_token() -> str:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Faltan SPOTIFY_CLIENT_ID y/o SPOTIFY_CLIENT_SECRET en las variables de entorno"
        )

    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError(
            f"Error de autenticacion con Spotify ({response.status_code}): {response.text}"
        )

    return response.json()["access_token"]


def _spotify_get(url: str, token: str, params: dict = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, params=params, timeout=15)

    if response.status_code == 401:
        raise ValueError(
            "Token de Spotify expirado o invalido. "
            "Por favor, reconecta tu cuenta de Spotify."
        )
    if response.status_code == 403:
        raise ValueError(
            "Acceso denegado por Spotify (403). "
            "En modo desarrollo, solo puedes analizar playlists que tu creaste o en las que colaboras. "
            "Asegurate de haber iniciado sesion con tu cuenta de Spotify."
        )
    if response.status_code == 404:
        raise ValueError(
            "Playlist no encontrada (404). "
            "Verifica que el enlace es correcto y que la playlist existe."
        )
    if response.status_code != 200:
        raise ValueError(
            f"Error de Spotify ({response.status_code}): {response.text[:200]}"
        )

    return response.json()


def _get_audio_features_map(token: str, track_ids: list[str]) -> dict:
    """
    Obtiene audio features por lote para los tracks dados.
    """
    if not track_ids:
        return {}

    feature_map = {}

    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i + 100]
        url = f"{SPOTIFY_API_BASE}/audio-features"
        params = {"ids": ",".join(batch)}

        try:
            data = _spotify_get(url, token, params)
            for item in data.get("audio_features", []):
                if not item or not item.get("id"):
                    continue

                feature_map[item["id"]] = {
                    "danceability": item.get("danceability", 0.0),
                    "energy": item.get("energy", 0.0),
                    "valence": item.get("valence", 0.0),
                    "tempo": item.get("tempo", 0.0),
                    "speechiness": item.get("speechiness", 0.0),
                    "acousticness": item.get("acousticness", 0.0),
                    "instrumentalness": item.get("instrumentalness", 0.0),
                    "liveness": item.get("liveness", 0.0),
                    "mode": item.get("mode", 0),
                }
        except Exception as exc:
            print(
                "[spotify_client] Advertencia: no se pudieron obtener audio features "
                f"para un lote de tracks - {exc}"
            )

    return feature_map


def get_playlist_info(token: str, playlist_id: str) -> dict:
    url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}"
    data = _spotify_get(url, token)

    images = data.get("images") or []
    tracks_obj = data.get("tracks") or data.get("items") or {}

    return {
        "name": data.get("name", "Playlist"),
        "description": data.get("description", ""),
        "owner": (data.get("owner") or {}).get("display_name", "Unknown"),
        "image_url": images[0]["url"] if images else None,
        "total_tracks": tracks_obj.get("total", 0),
    }


def get_playlist_tracks(
    playlist_url: str, max_tracks: int = 100, access_token: str = None
) -> tuple:
    if access_token:
        token = access_token
        print("[spotify_client] Usando token de usuario (PKCE)")
    else:
        print("[spotify_client] Usando Client Credentials (fallback)")
        token = _get_client_credentials_token()

    playlist_id = _extract_playlist_id(playlist_url)
    playlist_info = get_playlist_info(token, playlist_id)

    tracks = []
    offset = 0
    limit = 50

    while len(tracks) < max_tracks:
        url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items"
        params = {
            "offset": offset,
            "limit": limit,
            "fields": "items(item(id,name,artists(id,name),album,duration_ms,external_ids)),next",
        }

        results = _spotify_get(url, token, params)
        items = results.get("items", [])
        if not items:
            break

        for entry in items:
            item = entry.get("item") or entry.get("track")
            if not item or not item.get("id"):
                continue

            artist_name = (
                item["artists"][0]["name"] if item.get("artists") else "Unknown Artist"
            )
            artist_id = item["artists"][0].get("id") if item.get("artists") else None
            name = item.get("name", "Unknown")

            tracks.append(
                {
                    "track_id": item["id"],
                    "artist_id": artist_id,
                    "name": name,
                    "artist": artist_name,
                    "album": item.get("album", {}).get("name", ""),
                    "isrc": (item.get("external_ids") or {}).get("isrc"),
                    "text": f"{name} {artist_name}",
                    "duration_ms": item.get("duration_ms", 0),
                }
            )

            if len(tracks) >= max_tracks:
                break

        if not results.get("next"):
            break
        offset += limit

    audio_features_map = _get_audio_features_map(
        token, [track["track_id"] for track in tracks if track.get("track_id")]
    )
    for track in tracks:
        track["audio_features"] = audio_features_map.get(track["track_id"], {})

    print("[spotify_client] Obteniendo letras reales desde Musixmatch...")
    tracks = enrich_tracks_with_lyrics(tracks)

    return playlist_info, tracks
