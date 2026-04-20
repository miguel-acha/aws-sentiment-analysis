# -*- coding: utf-8 -*-
"""
test_credentials.py - Verificar credenciales de Spotify paso a paso
"""
import os, sys, re, io

# Fix encoding Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK] .env cargado")
except ImportError:
    print("[!] python-dotenv no instalado, usando variables del sistema")

client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

print("\n" + "="*60)
print("PASO 1: Variables de entorno")
print("="*60)
print(f"  CLIENT_ID:     {('[OK] ' + client_id[:8] + '...') if client_id else '[FALTA]'}")
print(f"  CLIENT_SECRET: {('[OK] ' + client_secret[:8] + '...') if client_secret else '[FALTA]'}")

if not client_id or not client_secret:
    print("\n[ERROR] Falta alguna variable. No se puede continuar.")
    sys.exit(1)

print("\n" + "="*60)
print("PASO 2: Autenticacion (Client Credentials)")
print("="*60)

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    print("  spotipy importado OK")
except ImportError:
    print("[ERROR] spotipy no instalado. pip install spotipy")
    sys.exit(1)

try:
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    token_info = auth_manager.get_access_token(as_dict=True)
    print(f"  [OK] Token: {token_info['access_token'][:20]}...")
    print(f"  [OK] Expira en: {token_info.get('expires_in', '?')} seg")
except Exception as e:
    print(f"  [ERROR] Autenticacion fallida: {e}")
    print("  -> Verifica CLIENT_ID y CLIENT_SECRET en https://developer.spotify.com/dashboard")
    sys.exit(1)

print("\n" + "="*60)
print("PASO 3: Acceso a playlist publica (Today's Top Hits)")
print("="*60)

TEST_ID = "37i9dQZF1DXcBWIGoYBM5M"

try:
    result = sp.playlist(TEST_ID, fields="name,owner,tracks(total)")
    name = result.get("name", "?")
    owner = result.get("owner", {}).get("display_name", "?")
    total = result.get("tracks", {}).get("total", "?")
    print(f"  [OK] Playlist: {name}")
    print(f"  [OK] Owner: {owner}")
    print(f"  [OK] Total tracks: {total}")
except spotipy.exceptions.SpotifyException as e:
    print(f"  [ERROR] HTTP {e.http_status}: {e.msg}")
    if e.http_status == 401:
        print("  -> Credenciales invalidas o expiradas")
    elif e.http_status == 403:
        print("  -> Sin permisos. Revisa tu app en Spotify Dashboard")
    elif e.http_status == 404:
        print("  -> Playlist no encontrada")
except Exception as e:
    print(f"  [ERROR] {type(e).__name__}: {e}")

print("\n" + "="*60)
print("PASO 4: Obtener primeras 3 canciones")
print("="*60)

try:
    tracks_result = sp.playlist_tracks(TEST_ID, limit=3, fields="items(track(name,artists(name)))")
    items = tracks_result.get("items", [])
    if items:
        for i, item in enumerate(items, 1):
            track = item.get("track", {})
            tname = track.get("name", "?")
            artist = track.get("artists", [{}])[0].get("name", "?")
            print(f"  {i}. {tname} - {artist}")
        print("\n  [OK] Todo funciona correctamente!")
    else:
        print("  [!] No se obtuvieron canciones")
except Exception as e:
    print(f"  [ERROR] {type(e).__name__}: {e}")

print("\n" + "="*60)
print("RESUMEN")
print("="*60)
print("Si todo muestra [OK], las credenciales estan bien.")
print("El problema seria que las variables NO llegan a Lambda en Amplify.")
print("Verifica en la consola de AWS Lambda -> Configuration -> Environment variables:")
print("  - SPOTIFY_CLIENT_ID")
print("  - SPOTIFY_CLIENT_SECRET")
print("  - S3_BUCKET_NAME")
