"""
lambda_handler.py
-----------------
Punto de entrada de AWS Lambda.
Orquesta todos los módulos en orden y retorna JSON con el resultado.

Estructura del evento de entrada:
{
    "playlist_url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
    "max_tracks": 50   (opcional, default 50)
}
"""

import json
import os
import sys
import traceback

# Asegurar que el directorio src esté en el path (para import local)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_client import get_playlist_tracks
from sentiment_analyzer import analyze_tracks
from aggregator import aggregate
from chart_generator import generate_report_png
from s3_uploader import upload_report, ensure_bucket_exists


# ─── CORS headers ────────────────────────────────────────────────────────────
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
    "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    "Content-Type": "application/json",
}


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event: dict, context) -> dict:
    """
    Función principal de Lambda.

    Args:
        event: Dict con { playlist_url, max_tracks? }
        context: Lambda context (no se usa directamente)

    Returns:
        Response HTTP con statusCode, headers y body JSON
    """
    print(f"[lambda_handler] Evento recibido: {json.dumps(event)}")

    # ── Preflight CORS ───────────────────────────────────────────────────────
    if event.get("httpMethod") == "OPTIONS":
        return _response(200, {"message": "OK"})

    # ── Parsear body ─────────────────────────────────────────────────────────
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        elif isinstance(event.get("body"), dict):
            body = event["body"]
        else:
            body = event  # Invocación directa (test en consola Lambda)
    except json.JSONDecodeError as e:
        return _response(400, {"error": f"Body inválido: {str(e)}"})

    playlist_url = body.get("playlist_url", "").strip()
    max_tracks   = int(body.get("max_tracks", 50))

    if not playlist_url:
        return _response(400, {"error": "Se requiere 'playlist_url' en el body"})

    if max_tracks < 1 or max_tracks > 200:
        return _response(400, {"error": "'max_tracks' debe estar entre 1 y 200"})

    # ── Pipeline principal ───────────────────────────────────────────────────
    try:
        # 1. Obtener canciones de Spotify
        print("[lambda_handler] Paso 1: Obteniendo tracks de Spotify...")
        playlist_info, tracks = get_playlist_tracks(playlist_url, max_tracks=max_tracks)
        print(f"[lambda_handler] Playlist: '{playlist_info['name']}' — {len(tracks)} tracks")

        if not tracks:
            return _response(404, {"error": "No se encontraron canciones en la playlist"})

        # 2. Analizar sentimiento con Comprehend
        print("[lambda_handler] Paso 2: Analizando sentimientos con Comprehend...")
        analyzed = analyze_tracks(tracks)

        # 3. Agregar resultados
        print("[lambda_handler] Paso 3: Agregando resultados...")
        summary = aggregate(analyzed)
        print(f"[lambda_handler] Resumen: {summary['dominant']} ({summary['weighted_score']:+.2f}) — {summary['vibe_label']}")

        # 4. Generar PNG del reporte
        print("[lambda_handler] Paso 4: Generando PNG...")
        png_bytes = generate_report_png(analyzed, summary, playlist_info)

        # 5. Subir a S3
        print("[lambda_handler] Paso 5: Subiendo a S3...")
        bucket = os.environ.get("S3_BUCKET_NAME", "spotify-sentiment-reports")
        ensure_bucket_exists(bucket)

        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        upload_result = upload_report(png_bytes, playlist_id)

        # 6. Preparar respuesta
        # Serializar tracks sin datos innecesarios para el frontend
        tracks_payload = [
            {
                "track_id":  t["track_id"],
                "name":      t["name"],
                "artist":    t["artist"],
                "album":     t.get("album", ""),
                "sentiment": t["sentiment"],
                "scores":    t["scores"],
                "popularity": t.get("popularity", 0),
            }
            for t in analyzed
        ]

        result = {
            "playlist": playlist_info,
            "summary": {
                "total":          summary["total"],
                "dominant":       summary["dominant"],
                "counts":         summary["counts"],
                "percentages":    summary["percentages"],
                "weighted_score": summary["weighted_score"],
                "vibe_label":     summary["vibe_label"],
            },
            "tracks":  tracks_payload,
            "png_url": upload_result["url"],
        }

        print("[lambda_handler] ✅ Pipeline completo exitosamente.")
        return _response(200, result)

    except ValueError as e:
        print(f"[lambda_handler] ValueError: {e}")
        return _response(400, {"error": str(e)})
    except Exception as e:
        print(f"[lambda_handler] Error inesperado: {e}")
        traceback.print_exc()
        return _response(500, {"error": "Error interno del servidor", "detail": str(e)})


# ─── Ejecución local para testing ────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    test_event = {
        "playlist_url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        "max_tracks": 10,
    }

    result = handler(test_event, None)
    print("\n--- RESULTADO ---")
    body = json.loads(result["body"])
    print(f"Status: {result['statusCode']}")
    if result["statusCode"] == 200:
        print(f"Playlist: {body['playlist']['name']}")
        print(f"Vibe: {body['summary']['vibe_label']} ({body['summary']['weighted_score']:+.2f})")
        print(f"PNG: {body['png_url']}")
    else:
        print(f"Error: {body['error']}")
