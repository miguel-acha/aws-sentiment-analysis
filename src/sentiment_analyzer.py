"""
sentiment_analyzer.py
----------------------
Recibe la lista de canciones y usa Amazon Comprehend para
detectar el sentimiento de cada una.

Idiomas soportados por detect_sentiment:
    en, es, fr, de, it, pt, ar, hi, ja, ko, zh, zh-TW

Si el idioma detectado no está soportado → fallback a NEUTRAL.
"""

import os
import boto3
from botocore.exceptions import ClientError

# Idiomas soportados por detect_sentiment en Amazon Comprehend
SUPPORTED_LANGUAGES = {
    "en", "es", "fr", "de", "it", "pt", "ar", "hi", "ja", "ko", "zh", "zh-TW"
}


def _get_comprehend_client():
    """Crea el cliente de Comprehend con la región configurada."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client("comprehend", region_name=region)


def _detect_language(client, text: str) -> str:
    """Detecta el idioma dominante del texto. Retorna el code o 'en' por defecto."""
    try:
        response = client.detect_dominant_language(Text=text[:300])  # Límite de chars
        languages = response.get("Languages", [])
        if languages:
            # Retornar el idioma con mayor score de confianza
            return max(languages, key=lambda x: x["Score"])["LanguageCode"]
    except ClientError as e:
        print(f"[sentiment_analyzer] Error detectando idioma: {e}")
    return "en"


def _detect_sentiment(client, text: str, language_code: str) -> dict:
    """
    Llama a Comprehend detect_sentiment.
    Retorna dict con sentiment y scores.
    """
    try:
        response = client.detect_sentiment(Text=text[:5000], LanguageCode=language_code)
        return {
            "sentiment": response["Sentiment"],  # POSITIVE | NEGATIVE | NEUTRAL | MIXED
            "scores": {
                "Positive": round(response["SentimentScore"]["Positive"], 4),
                "Negative": round(response["SentimentScore"]["Negative"], 4),
                "Neutral": round(response["SentimentScore"]["Neutral"], 4),
                "Mixed": round(response["SentimentScore"]["Mixed"], 4),
            },
        }
    except ClientError as e:
        print(f"[sentiment_analyzer] Error en detect_sentiment: {e}")
        return {
            "sentiment": "NEUTRAL",
            "scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 1.0, "Mixed": 0.0},
        }


def analyze_tracks(tracks: list[dict]) -> list[dict]:
    """
    Analiza el sentimiento de cada canción usando Amazon Comprehend.

    Args:
        tracks: Lista de dicts con al menos { track_id, name, artist, text }

    Returns:
        Lista de dicts con { track_id, name, artist, album, sentiment, scores }
    """
    client = _get_comprehend_client()
    results = []

    for i, track in enumerate(tracks):
        text = track.get("text", f"{track['name']} {track['artist']}")
        print(f"[{i+1}/{len(tracks)}] Analizando: {track['name']} — {track['artist']}")

        # 1. Detectar idioma
        lang_code = _detect_language(client, text)

        # 2. Verificar soporte — fallback a NEUTRAL si no soportado
        if lang_code not in SUPPORTED_LANGUAGES:
            print(f"  ⚠ Idioma '{lang_code}' no soportado → NEUTRAL")
            result = {
                "sentiment": "NEUTRAL",
                "scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 1.0, "Mixed": 0.0},
            }
        else:
            # 3. Analizar sentimiento
            result = _detect_sentiment(client, text, lang_code)

        results.append(
            {
                "track_id": track["track_id"],
                "name": track["name"],
                "artist": track["artist"],
                "album": track.get("album", ""),
                "popularity": track.get("popularity", 0),
                "duration_ms": track.get("duration_ms", 0),
                "sentiment": result["sentiment"],
                "scores": result["scores"],
                "detected_language": lang_code,
            }
        )

    return results


if __name__ == "__main__":
    # Test rápido con datos mock
    mock_tracks = [
        {"track_id": "1", "name": "Happy", "artist": "Pharrell Williams", "text": "Happy Pharrell Williams"},
        {"track_id": "2", "name": "Creep", "artist": "Radiohead", "text": "Creep Radiohead"},
        {"track_id": "3", "name": "Shape of You", "artist": "Ed Sheeran", "text": "Shape of You Ed Sheeran"},
    ]
    results = analyze_tracks(mock_tracks)
    for r in results:
        print(f"{r['name']}: {r['sentiment']} {r['scores']}")
