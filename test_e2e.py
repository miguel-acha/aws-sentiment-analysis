# -*- coding: utf-8 -*-
"""Ver respuesta RAW de la API para playlists"""
import os, sys, io, json, base64, requests
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

pl_id = "79emz4GMzwgJaytiuczD0D"

# GET /playlists/{id} - respuesta completa
print(f"GET /playlists/{pl_id}")
resp = requests.get(f"https://api.spotify.com/v1/playlists/{pl_id}", headers=headers)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    print(f"Name: {data.get('name')}")
    print(f"Public: {data.get('public')}")
    print(f"Collaborative: {data.get('collaborative')}")
    print(f"Owner: {data.get('owner',{}).get('display_name')}")
    
    tracks = data.get("tracks", {})
    print(f"tracks.total: {tracks.get('total')}")
    print(f"tracks.items count: {len(tracks.get('items', []))}")
    print(f"tracks.next: {tracks.get('next')}")
    
    # Mostrar los primeros items si hay
    for i, item in enumerate(tracks.get("items", [])[:3]):
        t = item.get("track", {})
        if t:
            print(f"  Track {i+1}: {t.get('name')} - {t.get('artists',[{}])[0].get('name')}")

    # GET /playlists/{id}/tracks - endpoint separado  
    print(f"\nGET /playlists/{pl_id}/tracks")
    resp2 = requests.get(
        f"https://api.spotify.com/v1/playlists/{pl_id}/tracks",
        headers=headers,
        params={"limit": 5}
    )
    print(f"Status: {resp2.status_code}")
    if resp2.status_code == 200:
        data2 = resp2.json()
        print(f"Total: {data2.get('total')}")
        for item in data2.get("items",[])[:3]:
            t = item.get("track",{})
            if t:
                print(f"  - {t.get('name')} - {t.get('artists',[{}])[0].get('name')}")
    else:
        print(f"Error: {resp2.text[:200]}")
        
    # Intentar otro endpoint: GET /playlists/{id} con fields que incluyen tracks
    print(f"\nGET /playlists/{pl_id}?fields=tracks.items(track(name,artists))")
    resp3 = requests.get(
        f"https://api.spotify.com/v1/playlists/{pl_id}",
        headers=headers,
        params={"fields": "tracks.items(track(name,artists))"}
    )
    print(f"Status: {resp3.status_code}")
    if resp3.status_code == 200:
        data3 = resp3.json()
        items3 = data3.get("tracks",{}).get("items",[])
        print(f"Items: {len(items3)}")
        for item in items3[:3]:
            t = item.get("track",{})
            if t:
                print(f"  - {t.get('name')} - {t.get('artists',[{}])[0].get('name')}")
    else:
        print(f"Error: {resp3.text[:200]}")
else:
    print(f"Error: {resp.text[:300]}")
