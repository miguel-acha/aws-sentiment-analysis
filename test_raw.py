# -*- coding: utf-8 -*-
"""
Test directo con requests - sin spotipy, para aislar el problema
"""
import os, sys, io, json, base64, requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

client_id = os.environ["SPOTIFY_CLIENT_ID"]
client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]

# ── Paso 1: Obtener token manualmente ────────────────────────────────────────
print("PASO 1: Obtener token con requests (sin spotipy)")
auth_str = f"{client_id}:{client_secret}"
auth_b64 = base64.b64encode(auth_str.encode()).decode()

resp = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={"Authorization": f"Basic {auth_b64}"},
    data={"grant_type": "client_credentials"},
)

print(f"  Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"  [ERROR] No se pudo obtener token: {resp.text}")
    sys.exit(1)

token_data = resp.json()
token = token_data["access_token"]
print(f"  [OK] Token: {token[:25]}...")

headers = {"Authorization": f"Bearer {token}"}

# ── Paso 2: Buscar artista ───────────────────────────────────────────────────
print("\nPASO 2: Buscar artista 'Bad Bunny'")
resp = requests.get(
    "https://api.spotify.com/v1/search",
    headers=headers,
    params={"q": "Bad Bunny", "type": "artist", "limit": 1}
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    items = data.get("artists", {}).get("items", [])
    if items:
        print(f"  [OK] {items[0]['name']} - ID: {items[0]['id']}")
    else:
        print("  [!] Sin resultados")
else:
    print(f"  [ERROR] {resp.text[:200]}")

# ── Paso 3: Obtener track ───────────────────────────────────────────────────
print("\nPASO 3: Obtener track 'Blinding Lights'")
resp = requests.get(
    "https://api.spotify.com/v1/tracks/0VjIjW4GlUZAMYd2vXMi4e",
    headers=headers,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  [OK] {data['name']} - {data['artists'][0]['name']}")
else:
    print(f"  [ERROR] {resp.text[:300]}")

# ── Paso 4: Playlist Today's Top Hits ────────────────────────────────────────
print("\nPASO 4: Playlist 'Today's Top Hits'")
resp = requests.get(
    "https://api.spotify.com/v1/playlists/37i9dQZF1DXcBWIGoYBM5M",
    headers=headers,
    params={"fields": "name,tracks(total)"}
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  [OK] {data.get('name')} - {data.get('tracks',{}).get('total')} tracks")
else:
    print(f"  [ERROR] {resp.text[:300]}")

# ── Paso 5: Playlist con market ──────────────────────────────────────────────
print("\nPASO 5: Playlist con market=US")
resp = requests.get(
    "https://api.spotify.com/v1/playlists/37i9dQZF1DXcBWIGoYBM5M",
    headers=headers,
    params={"market": "US"}
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  [OK] {data.get('name')}")
else:
    print(f"  [ERROR] {resp.text[:300]}")

# ── Paso 6: Mi perfil (deberia fallar con client credentials) ────────────────
print("\nPASO 6: Featured playlists")
resp = requests.get(
    "https://api.spotify.com/v1/browse/featured-playlists",
    headers=headers,
    params={"limit": 3, "country": "US"}
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    for pl in data.get("playlists", {}).get("items", []):
        print(f"  - {pl['name']} (ID: {pl['id']})")
    # Probar la primera playlist encontrada
    if data.get("playlists", {}).get("items"):
        test_pl_id = data["playlists"]["items"][0]["id"]
        print(f"\n  Probando playlist encontrada: {test_pl_id}")
        resp2 = requests.get(
            f"https://api.spotify.com/v1/playlists/{test_pl_id}",
            headers=headers,
            params={"fields": "name,tracks(total)"}
        )
        print(f"  Status: {resp2.status_code}")
        if resp2.status_code == 200:
            d2 = resp2.json()
            print(f"  [OK] {d2.get('name')} - {d2.get('tracks',{}).get('total')} tracks")
        else:
            print(f"  [ERROR] {resp2.text[:200]}")
else:
    print(f"  [ERROR] {resp.text[:300]}")

print("\n" + "="*60)
print("Si NADA funciona, el problema es tu app de Spotify.")
print("Intenta CREAR UNA APP NUEVA en el dashboard.")
print("="*60)
