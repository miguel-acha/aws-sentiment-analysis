# -*- coding: utf-8 -*-
"""Test minimo - probar endpoints que no requieren playlist"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
))

# Test 1: Buscar un artista (esto NO requiere playlist)
print("TEST 1: Buscar artista 'Bad Bunny'")
try:
    r = sp.search(q="Bad Bunny", type="artist", limit=1)
    artist = r["artists"]["items"][0]
    print(f"  [OK] {artist['name']} - Followers: {artist['followers']['total']}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 2: Obtener un track por ID
print("\nTEST 2: Obtener track por ID (Blinding Lights)")
try:
    track = sp.track("0VjIjW4GlUZAMYd2vXMi4e")
    print(f"  [OK] {track['name']} - {track['artists'][0]['name']}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 3: Probar playlist con market explicitamente
print("\nTEST 3: Playlist con market='US'")
try:
    result = sp.playlist("37i9dQZF1DXcBWIGoYBM5M", market="US")
    print(f"  [OK] {result['name']} - {result['tracks']['total']} tracks")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 4: Probar OTRA playlist publica
print("\nTEST 4: Playlist 'Rock Classics' (otra playlist publica)")
try:
    result = sp.playlist("37i9dQZF1DWXRqgorJj26U", market="US")
    print(f"  [OK] {result['name']} - {result['tracks']['total']} tracks")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 5: Probar playlist del usuario
print("\nTEST 5: Listar categorias (endpoint publico)")
try:
    cats = sp.categories(limit=5, country="US")
    for cat in cats["categories"]["items"]:
        print(f"  - {cat['name']}")
    print("  [OK]")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "="*60)
print("DIAGNOSTICO:")
print("="*60)
print("Si TEST 1 y 2 funcionan pero TEST 3 y 4 fallan,")
print("tu app de Spotify esta en Development Mode.")
print("")
print("SOLUCION: Ve a https://developer.spotify.com/dashboard")
print("  1. Selecciona tu app")
print("  2. Ve a Settings")
print("  3. Busca 'Extended Quota Mode' o 'Request Extension'")
print("  4. O simplemente asegurate de que el 'Web API' esta habilitado")
