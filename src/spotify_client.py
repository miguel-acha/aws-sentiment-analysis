"""
spotify_client.py
-----------------
Autentica con Spotify y extrae las canciones de una playlist.

Actualizado para los cambios de la API de febrero 2026:
- Usa el nuevo endpoint GET /playlists/{id}/items (reemplaza /tracks)
- Parsea el campo 'item' en lugar de 'track'
- Acepta access_token de usuario (Authorization Code Flow PKCE)
- Fallback a Client Credentials si no se pasa token
- Campo 'popularity' eliminado (ya no disponible en la API)

Retorna:
    Lista de dicts con { track_id, name, artist, text }
    donde `text` = "nombre + artista" (MVP — sin letras reales)
"""

import re
import os
import base64
import requests


# ─── Spotify API Base URL ────────────────────────────────────────────────────
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


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


def _get_client_credentials_token() -> str:
    """
    Obtiene un token via Client Credentials Flow (fallback).
    Solo funciona para playlists del dueño de la app en Dev Mode.
    """
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Faltan SPOTIFY_CLIENT_ID y/o SPOTIFY_CLIENT_SECRET en las variables de entorno"
        )

    # Codificar credenciales en Base64
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
    """Realiza un GET autenticado a la API de Spotify."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, params=params, timeout=15)

    if response.status_code == 401:
        raise ValueError(
            "Token de Spotify expirado o invalido. "
            "Por favor, reconecta tu cuenta de Spotify."
        )
    elif response.status_code == 403:
        raise ValueError(
            "Acceso denegado por Spotify (403). "
            "En modo desarrollo, solo puedes analizar playlists que tu creaste o en las que colaboras. "
            "Asegurate de haber iniciado sesion con tu cuenta de Spotify."
        )
    elif response.status_code == 404:
        raise ValueError(
            "Playlist no encontrada (404). "
            "Verifica que el enlace es correcto y que la playlist existe."
        )
    elif response.status_code != 200:
        raise ValueError(
            f"Error de Spotify ({response.status_code}): {response.text[:200]}"
        )

    return response.json()


def get_playlist_info(token: str, playlist_id: str) -> dict:
    """Retorna metadata basica de la playlist (nombre, imagen, owner)."""
    url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}"
    # Sin 'fields' para mayor compatibilidad — la API puede rechazar campos inválidos
    data = _spotify_get(url, token)

    images = data.get("images") or []
    # El campo puede ser 'tracks' o 'items' según la versión de la API
    tracks_obj = data.get("tracks") or data.get("items") or {}

    return {
        "name":         data.get("name", "Playlist"),
        "description":  data.get("description", ""),
        "owner":        (data.get("owner") or {}).get("display_name", "Unknown"),
        "image_url":    images[0]["url"] if images else None,
        "total_tracks": tracks_obj.get("total", 0),
    }


def get_playlist_tracks(
    playlist_url: str, max_tracks: int = 100, access_token: str = None
) -> tuple:
    """
    Extrae las canciones de una playlist de Spotify.

    Usa el nuevo endpoint GET /playlists/{id}/items (Feb 2026).

    Args:
        playlist_url: URL completa o ID de la playlist
        max_tracks: Maximo de canciones a procesar
        access_token: Token de usuario (PKCE flow). Si es None, usa Client Credentials.

    Returns:
        Tuple (playlist_info, tracks)
        tracks: lista de dicts { track_id, name, artist, album, text, duration_ms }
    """
    # Determinar el token a usar
    if access_token:
        token = access_token
        print("[spotify_client] Usando token de usuario (PKCE)")
    else:
        print("[spotify_client] Usando Client Credentials (fallback)")
        token = _get_client_credentials_token()

    playlist_id = _extract_playlist_id(playlist_url)

    # Obtener info de la playlist
    playlist_info = get_playlist_info(token, playlist_id)

    # Paginar y extraer tracks usando el NUEVO endpoint /items
    tracks = []
    offset = 0
    limit = 50  # Maximo permitido por la API

    while len(tracks) < max_tracks:
        url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/items"
        params = {
            "offset": offset,
            "limit": limit,
            # Feb 2026: usar 'item' en lugar de 'track' en fields
            "fields": "items(item(id,name,artists,album,duration_ms)),next",
        }

        results = _spotify_get(url, token, params)

        items = results.get("items", [])
        if not items:
            break

        for entry in items:
            # Feb 2026: el campo 'track' fue renombrado a 'item'
            # Soportamos ambos para compatibilidad
            item = entry.get("item") or entry.get("track")
            if not item or not item.get("id"):
                continue  # Saltar items locales o nulos

            artist = (
                item["artists"][0]["name"]
                if item.get("artists")
                else "Unknown Artist"
            )
            name = item.get("name", "Unknown")

            tracks.append(
                {
                    "track_id": item["id"],
                    "name": name,
                    "artist": artist,
                    "album": item.get("album", {}).get("name", ""),
                    # MVP: usamos nombre + artista como texto para Comprehend
                    # Fase 2: reemplazar con letras reales de Genius API
                    "text": f"{name} {artist}",
                    "duration_ms": item.get("duration_ms", 0),
                    # Feb 2026: 'popularity' eliminado de la API
                }
            )

            if len(tracks) >= max_tracks:
                break

        if not results.get("next"):
            break
        offset += limit

    return playlist_info, tracks


if __name__ == "__main__":
    # Test rapido
    from dotenv import load_dotenv

    load_dotenv()

    test_url = "https://open.spotify.com/playlist/1BmqpSfccNZMPtkMpIl2FZ"
    info, tracks = get_playlist_tracks(test_url, max_tracks=5)
    print(f"Playlist: {info['name']} ({info['total_tracks']} canciones)")
    for t in tracks:
        print(f"  - {t['name']} | {t['artist']}")
