# -*- coding: utf-8 -*-
"""Test rapido: playlist acceso con nuevas credenciales"""
import os, sys, io, base64, requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dotenv import load_dotenv
load_dotenv()

client_id = os.environ["SPOTIFY_CLIENT_ID"]
client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]

auth_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
resp = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={"Authorization": f"Basic {auth_b64}"},
    data={"grant_type": "client_credentials"},
)
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[OK] Token obtenido\n")

# Playlist Today's Top Hits
print("TEST 1: Playlist Today's Top Hits (Spotify curada)")
resp = requests.get(
    "https://api.spotify.com/v1/playlists/37i9dQZF1DXcBWIGoYBM5M",
    headers=headers,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    d = resp.json()
    print(f"  [OK] {d.get('name')} - {d.get('tracks',{}).get('total')} tracks")
else:
    print(f"  [FALLO] {resp.json().get('error',{}).get('message','?')}")

# Playlist buscada por search
print("\nTEST 2: Buscar playlist y acceder")
resp = requests.get(
    "https://api.spotify.com/v1/search",
    headers=headers,
    params={"q": "top hits", "type": "playlist", "limit": 5}
)
if resp.status_code == 200:
    items = [i for i in resp.json().get("playlists",{}).get("items",[]) if i is not None]
    for pl in items[:3]:
        print(f"  - {pl.get('name','?')} (ID: {pl.get('id','?')})")
    
    if items:
        pl_id = items[0]["id"]
        print(f"\n  Accediendo playlist {pl_id}...")
        resp2 = requests.get(f"https://api.spotify.com/v1/playlists/{pl_id}", headers=headers)
        print(f"  Status: {resp2.status_code}")
        if resp2.status_code == 200:
            d = resp2.json()
            print(f"  [OK] {d.get('name')} - {d.get('tracks',{}).get('total')} tracks")
            for t in d.get("tracks",{}).get("items",[])[:3]:
                tr = t.get("track",{})
                if tr:
                    print(f"    - {tr.get('name','?')} - {tr.get('artists',[{}])[0].get('name','?')}")
        else:
            print(f"  [FALLO] {resp2.json().get('error',{}).get('message','?')}")

# Probar con spotipy tambien
print("\n\nTEST 3: Probar con SPOTIPY (como lo usa tu app)")
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
))

try:
    pl = sp.playlist("37i9dQZF1DXcBWIGoYBM5M", fields="name,tracks(total)")
    print(f"  [OK] {pl['name']} - {pl['tracks']['total']} tracks")
except Exception as e:
    print(f"  [FALLO] {e}")

try:
    tracks = sp.playlist_tracks("37i9dQZF1DXcBWIGoYBM5M", limit=3)
    for item in tracks["items"]:
        t = item["track"]
        if t:
            print(f"    - {t['name']} - {t['artists'][0]['name']}")
    print("  [OK] playlist_tracks funciona!")
except Exception as e:
    print(f"  [FALLO] {e}")
