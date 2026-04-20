import os
import sys
from dotenv import load_dotenv

# Asegurar que el path incluye src para importar spotify_client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from spotify_client import get_playlist_tracks, _get_client_credentials_token
import traceback

def test_api():
    load_dotenv()
    
    print("=== TEST SPOTIFY_CLIENT API MIGRATION (FEB 2026) ===")
    
    # 1. Test Client Credentials flow fallback
    try:
        token = _get_client_credentials_token()
        print(f"[OK] Token CC fallback obtenido: {token[:15]}...")
    except Exception as e:
        print(f"[ERROR] No se pudo obtener CC token: {e}")
        return

    # Usamos una playlist de dueñia para testear, probaremos Today's Top Hits
    # IMPORTANTE: En dev mode con Client Credentials provocara 403 sobre el endpoint /items!
    # El GET /playlists/{id} devolverá 200, pero GET /playlists/{id}/items devolverá 403.
    # El test pasara la 1ra parte y deberia capturar el 403 gracefully.
    
    playlist_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    print(f"\n[TEST 1] Fallback (Client Credentials) vs Playlist publica no propia")
    print(f"         Deberia dar Error 403 con nuestro mensaje custom.")
    
    try:
        info, tracks = get_playlist_tracks(playlist_url, max_tracks=5)
        print(f"[FALLO LOGICO] Deberia haber tirado ValueError con 403, devolvio {len(tracks)} tracks??")
    except ValueError as e:
        if "403" in str(e):
            print(f"[OK ESPERADO] {e}")
        else:
            print(f"[ERROR INESPERADO] {e}")
    except Exception as e:
        print(f"[ERROR INESPERADO] {e}")
        traceback.print_exc()
        
if __name__ == "__main__":
    test_api()
