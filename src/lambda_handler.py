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
    Compatible con HTTP API v2 (payload format 2.0) y REST API v1.

    Args:
        event: Evento de API Gateway o invocación directa
        context: Lambda context

    Returns:
        Response HTTP con statusCode, headers y body JSON
    """
    print(f"[lambda_handler] Evento recibido tipo={type(event).__name__}")

    # ── Normalizar event si llega como string ────────────────────────────────
    # serverless invoke --data puede enviar el payload como string
    if isinstance(event, str):
        try:
            event = json.loads(event)
        except json.JSONDecodeError:
            return _response(400, {"error": "Evento inválido: no es JSON"})

    print(f"[lambda_handler] Evento: {json.dumps(event)}")

    # ── Detectar formato del evento ──────────────────────────────────────────
    # HTTP API v2 usa 'routeKey' y 'requestContext.http.method'
    # REST API v1 usa 'httpMethod'
    # Invocación directa (test) no tiene ninguno de los dos

    # ── Preflight CORS (v1 y v2) ─────────────────────────────────────────────
    http_method = (
        event.get("httpMethod")                                          # REST v1
        or (event.get("requestContext", {}).get("http", {}).get("method"))  # HTTP v2
        or ""
    )
    if http_method.upper() == "OPTIONS":
        return _response(200, {"message": "OK"})

    # ── Parsear body ─────────────────────────────────────────────────────────
    try:
        raw_body = event.get("body")
        if isinstance(raw_body, str):
            body = json.loads(raw_body)
        elif isinstance(raw_body, dict):
            body = raw_body
        elif raw_body is None:
            # Invocación directa: el propio evento ES el body
            body = event
        else:
            body = event
    except json.JSONDecodeError as e:
        return _response(400, {"error": f"Body inválido: {str(e)}"})


    playlist_url = body.get("playlist_url", "").strip()
    max_tracks   = int(body.get("max_tracks", 50))
    spotify_token = body.get("spotify_token", "").strip() or None

    if not playlist_url:
        return _response(400, {"error": "Se requiere 'playlist_url' en el body"})

    if max_tracks < 1 or max_tracks > 200:
        return _response(400, {"error": "'max_tracks' debe estar entre 1 y 200"})

    # ── Pipeline principal ───────────────────────────────────────────────────
    try:
        # 1. Obtener canciones de Spotify
        print("[lambda_handler] Paso 1: Obteniendo tracks de Spotify...")
        playlist_info, tracks = get_playlist_tracks(
            playlist_url, 
            max_tracks=max_tracks, 
            access_token=spotify_token
        )
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

        # 4. Generar PNG y subir a S3 (opcional — si falla, continuamos sin PNG)
        png_url = None
        try:
            print("[lambda_handler] Paso 4: Generando PNG...")
            from chart_generator import generate_report_png

            png_bytes = generate_report_png(analyzed, summary, playlist_info)

            print("[lambda_handler] Paso 5: Subiendo a S3...")
            bucket = os.environ.get("S3_BUCKET_NAME", "spotify-sentiment-reports")
            ensure_bucket_exists(bucket)
            playlist_id = playlist_url.split("/")[-1].split("?")[0]
            upload_result = upload_report(png_bytes, playlist_id)
            png_url = upload_result.get("url")
            print(f"[lambda_handler] PNG subido: {png_url}")
        except Exception as png_err:
            print(f"[lambda_handler] Advertencia: PNG/S3 falló (no crítico): {png_err}")

        # 6. Preparar respuesta
        tracks_payload = [
            {
                "track_id":  t["track_id"],
                "name":      t["name"],
                "artist":    t["artist"],
                "album":     t.get("album", ""),
                "sentiment": t["sentiment"],
                "scores":    t["scores"],
                "lyric_sentiment": t.get("lyric_sentiment"),
                "lyric_scores": t.get("lyric_scores"),
                "vibe_score": t.get("vibe_score"),
                "audio_vibe_score": t.get("audio_vibe_score"),
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
                "average_track_score": summary.get("average_track_score"),
                "sentiment_balance": summary.get("sentiment_balance"),
                "vibe_label":     summary["vibe_label"],
                "ai_interpretation": summary.get("ai_interpretation", "No interpretation available."),
            },
            "tracks":  tracks_payload,
            "png_url": png_url,  # None si S3 falló
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
