"""
musixmatch_client.py
--------------------
Obtiene letras reales usando el paquete musicxmatch_api.

No requiere API key. Usa ISRC como metodo principal y busqueda por
nombre + artista como fallback.
"""

import time

from musicxmatch_api import MusixMatchAPI


def _extract_lyrics_body(response: dict) -> str | None:
    try:
        status = response["message"]["header"]["status_code"]
        if status != 200:
            return None

        lyrics_body = response["message"]["body"]["lyrics"]["lyrics_body"]
        if not lyrics_body:
            return None

        clean = lyrics_body.split("******* This Lyrics")[0].strip()
        return clean if clean else None
    except (KeyError, TypeError):
        return None


def _get_lyrics_by_isrc(api: MusixMatchAPI, isrc: str) -> str | None:
    try:
        response = api.get_track_lyrics(track_isrc=isrc)
        return _extract_lyrics_body(response)
    except Exception as exc:
        print(f"[musixmatch] Error buscando por ISRC {isrc}: {exc}")
        return None


def _get_lyrics_by_search(api: MusixMatchAPI, track_name: str, artist_name: str) -> str | None:
    try:
        query = f"{track_name} {artist_name}"
        response = api.search_tracks(query)

        status = response["message"]["header"]["status_code"]
        if status != 200:
            return None

        track_list = response["message"]["body"]["track_list"]
        if not track_list:
            return None

        for entry in track_list[:3]:
            track_id = entry["track"]["track_id"]
            lyrics_response = api.get_track_lyrics(track_id=track_id)
            lyrics = _extract_lyrics_body(lyrics_response)
            if lyrics:
                return lyrics

        return None
    except Exception as exc:
        print(f"[musixmatch] Error en busqueda '{track_name}' - {artist_name}: {exc}")
        return None


def enrich_tracks_with_lyrics(tracks: list[dict], delay_seconds: float = 0.3) -> list[dict]:
    """
    Agrega el campo `text` con letra real cuando existe.
    """
    print("[musixmatch] Inicializando cliente (resolviendo secret HMAC)...")
    try:
        api = MusixMatchAPI()
    except Exception as exc:
        print(f"[musixmatch] No se pudo inicializar el cliente: {exc}. Usando fallback.")
        for track in tracks:
            track["text"] = f"{track.get('name', '')} {track.get('artist', '')}".strip()
            track["has_lyrics"] = False
        return tracks

    print("[musixmatch] Cliente listo.")

    found = 0
    not_found = 0

    for index, track in enumerate(tracks):
        name = track.get("name", "")
        artist = track.get("artist", "")
        isrc = track.get("isrc")

        print(f"[musixmatch] [{index + 1}/{len(tracks)}] '{name}' - {artist}", end=" ")

        lyrics = None
        if isrc:
            lyrics = _get_lyrics_by_isrc(api, isrc)
            if lyrics:
                print("✓ (ISRC)")

        if not lyrics:
            lyrics = _get_lyrics_by_search(api, name, artist)
            if lyrics:
                print("✓ (busqueda)")

        if lyrics:
            track["text"] = lyrics
            track["has_lyrics"] = True
            found += 1
        else:
            print("✗ (sin letra - fallback)")
            track["text"] = f"{name} {artist}".strip()
            track["has_lyrics"] = False
            not_found += 1

        if delay_seconds > 0 and index < len(tracks) - 1:
            time.sleep(delay_seconds)

    print(
        f"[musixmatch] Completado: {found} con letra, "
        f"{not_found} sin letra (fallback) de {len(tracks)} total."
    )
    return tracks
