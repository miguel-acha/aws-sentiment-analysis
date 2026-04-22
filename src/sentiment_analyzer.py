"""
sentiment_analyzer.py
---------------------
Recibe la lista de canciones y usa Amazon Comprehend para detectar
sentimiento lirico. Luego combina ese resultado con senales musicales
de Spotify para calcular un vibe final mas cercano a la experiencia real.

Idiomas soportados por detect_sentiment:
    en, es, fr, de, it, pt, ar, hi, ja, ko, zh, zh-TW
"""

import os
import re

import boto3
from botocore.exceptions import ClientError

from text_preprocessor import preprocess_lyrics_for_comprehend


SUPPORTED_LANGUAGES = {
    "en", "es", "fr", "de", "it", "pt", "ar", "hi", "ja", "ko", "zh", "zh-TW"
}

PARTY_HINT_TERMS = (
    "fiesta",
    "baile",
    "celebration",
    "energy",
    "good mood",
    "enjoying",
    "confidence",
    "success",
    "style",
    "persona deseada",
    "desired person",
    "diversion",
    "alegria",
    "exito",
    "sensual",
)

NEGATIVE_HINT_TERMS = (
    "violence",
    "weapon",
    "threat",
    "conflict",
    "homicide",
    "heartbreak",
    "sadness",
    "broken",
    "odio",
    "dolor",
    "rejection",
    "hurt",
)


def _clamp(value: float, minimum: float = -1.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _safe_feature(audio_features: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(audio_features.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _get_comprehend_client():
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client("comprehend", region_name=region)


def _detect_language(client, text: str) -> str:
    try:
        response = client.detect_dominant_language(Text=text[:300])
        languages = response.get("Languages", [])
        if languages:
            return max(languages, key=lambda item: item["Score"])["LanguageCode"]
    except ClientError as exc:
        print(f"[sentiment_analyzer] Error detectando idioma: {exc}")
    return "en"


def _detect_sentiment(client, text: str, language_code: str) -> dict:
    try:
        response = client.detect_sentiment(Text=text[:5000], LanguageCode=language_code)
        return {
            "sentiment": response["Sentiment"],
            "scores": {
                "Positive": round(response["SentimentScore"]["Positive"], 4),
                "Negative": round(response["SentimentScore"]["Negative"], 4),
                "Neutral": round(response["SentimentScore"]["Neutral"], 4),
                "Mixed": round(response["SentimentScore"]["Mixed"], 4),
            },
        }
    except ClientError as exc:
        print(f"[sentiment_analyzer] Error en detect_sentiment: {exc}")
        return {
            "sentiment": "NEUTRAL",
            "scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 1.0, "Mixed": 0.0},
        }


def _sentiment_to_scalar(scores: dict) -> float:
    return round(scores.get("Positive", 0.0) - scores.get("Negative", 0.0), 4)


def _extract_semantic_hints(text: str) -> dict:
    lowered = (text or "").lower()
    party_hits = sum(lowered.count(term) for term in PARTY_HINT_TERMS)
    negative_hits = sum(lowered.count(term) for term in NEGATIVE_HINT_TERMS)
    romantic_hits = len(re.findall(r"\bdeseo\b|\bseduccion\b|\batraccion\b", lowered))

    return {
        "party_hits": party_hits,
        "negative_hits": negative_hits,
        "romantic_hits": romantic_hits,
    }


def _compute_audio_vibe_score(audio_features: dict) -> float:
    if not audio_features:
        return 0.0

    valence = _safe_feature(audio_features, "valence")
    energy = _safe_feature(audio_features, "energy")
    danceability = _safe_feature(audio_features, "danceability")
    tempo = _safe_feature(audio_features, "tempo")
    speechiness = _safe_feature(audio_features, "speechiness")
    acousticness = _safe_feature(audio_features, "acousticness")
    instrumentalness = _safe_feature(audio_features, "instrumentalness")
    mode = int(_safe_feature(audio_features, "mode", 0.0))

    score = 0.0
    score += (valence - 0.5) * 0.65
    score += (energy - 0.55) * 0.60
    score += (danceability - 0.55) * 0.65

    if 96 <= tempo <= 140:
        score += 0.08
    elif tempo > 140:
        score += 0.04

    if mode == 1:
        score += 0.05
    if acousticness >= 0.70 and energy < 0.45:
        score -= 0.08
    if speechiness >= 0.55 and valence < 0.30:
        score -= 0.08
    if instrumentalness >= 0.85 and energy < 0.40:
        score -= 0.04
    if danceability >= 0.82 and energy >= 0.78:
        score += 0.12
    if danceability >= 0.86 and valence >= 0.42:
        score += 0.08

    return round(_clamp(score), 4)


def _compute_hint_score(hints: dict) -> float:
    party_score = min(0.30, hints["party_hits"] * 0.05)
    romantic_score = min(0.10, hints["romantic_hits"] * 0.03)
    negative_score = min(0.30, hints["negative_hits"] * 0.06)
    return round(_clamp(party_score + romantic_score - negative_score, -0.5, 0.5), 4)


def _compute_final_vibe_score(lyric_score: float, audio_score: float, hints: dict, audio_features: dict) -> float:
    hint_score = _compute_hint_score(hints)
    has_audio = bool(audio_features)

    if has_audio:
        final_score = lyric_score * 0.28 + audio_score * 0.54 + hint_score * 0.18
    else:
        final_score = lyric_score * 0.72 + hint_score * 0.28

    danceability = _safe_feature(audio_features, "danceability")
    energy = _safe_feature(audio_features, "energy")
    valence = _safe_feature(audio_features, "valence")

    is_party_track = danceability >= 0.76 and energy >= 0.70
    is_strong_party_track = danceability >= 0.84 and energy >= 0.78
    is_really_dark = hints["negative_hits"] >= 2 and valence < 0.40

    if is_party_track and valence >= 0.34 and lyric_score > -0.60:
        final_score += 0.20
    if is_party_track and hints["party_hits"] >= 2 and lyric_score > -0.45:
        final_score += 0.12
    if is_strong_party_track and hints["negative_hits"] == 0 and lyric_score > -0.65:
        final_score = max(final_score, 0.18)
    if is_strong_party_track and valence >= 0.45 and lyric_score > -0.55:
        final_score = max(final_score, 0.24)
    if is_really_dark:
        final_score -= 0.12

    return round(_clamp(final_score), 4)


def _label_from_score(final_score: float, raw_scores: dict) -> str:
    positive = raw_scores.get("Positive", 0.0)
    negative = raw_scores.get("Negative", 0.0)
    mixed = raw_scores.get("Mixed", 0.0)

    if final_score >= 0.14:
        return "POSITIVE"
    if final_score <= -0.18:
        return "NEGATIVE"
    if abs(final_score) <= 0.08 and mixed >= 0.15 and positive >= 0.18 and negative >= 0.18:
        return "MIXED"
    return "NEUTRAL"


def _build_adjusted_scores(raw_scores: dict, lyric_score: float, final_score: float) -> dict:
    positive = float(raw_scores.get("Positive", 0.0))
    negative = float(raw_scores.get("Negative", 0.0))
    neutral = float(raw_scores.get("Neutral", 0.0))
    mixed = float(raw_scores.get("Mixed", 0.0))

    adjustment = final_score - lyric_score
    if adjustment > 0:
        positive += adjustment * 0.70
        negative -= adjustment * 0.45
        neutral -= adjustment * 0.25
    elif adjustment < 0:
        shift = abs(adjustment)
        negative += shift * 0.70
        positive -= shift * 0.45
        neutral -= shift * 0.25

    if abs(final_score) < 0.12:
        neutral += 0.18
    elif abs(final_score) > 0.40:
        neutral -= 0.12

    values = {
        "Positive": max(0.0, positive),
        "Negative": max(0.0, negative),
        "Neutral": max(0.0, neutral),
        "Mixed": max(0.0, mixed),
    }
    total = sum(values.values()) or 1.0

    normalized = {key: round(value / total, 4) for key, value in values.items()}
    diff = round(1.0 - sum(normalized.values()), 4)
    normalized["Neutral"] = round(max(0.0, normalized["Neutral"] + diff), 4)
    return normalized


def analyze_tracks(tracks: list[dict]) -> list[dict]:
    if not tracks:
        return []

    client = _get_comprehend_client()
    results = []

    for index, track in enumerate(tracks):
        raw_text = track.get("text", f"{track['name']} {track['artist']}")
        prepared = preprocess_lyrics_for_comprehend(raw_text)
        analysis_text = prepared["text"] or raw_text
        prep_stats = prepared["stats"]

        print(f"[{index + 1}/{len(tracks)}] Analizando: {track['name']} - {track['artist']}")
        print(
            "  [preprocess] "
            f"{prep_stats['original_chars']} -> {prep_stats['final_chars']} chars, "
            f"{prep_stats['slang_hits']} slang, "
            f"{prep_stats['duplicate_lines_trimmed']} lineas deduplicadas"
        )

        lang_code = _detect_language(client, analysis_text)

        if lang_code not in SUPPORTED_LANGUAGES:
            print(f"  [warn] Idioma '{lang_code}' no soportado -> NEUTRAL")
            lyric_result = {
                "sentiment": "NEUTRAL",
                "scores": {"Positive": 0.0, "Negative": 0.0, "Neutral": 1.0, "Mixed": 0.0},
            }
        else:
            lyric_result = _detect_sentiment(client, analysis_text, lang_code)

        lyric_score = _sentiment_to_scalar(lyric_result["scores"])
        audio_features = track.get("audio_features") or {}
        audio_vibe_score = _compute_audio_vibe_score(audio_features)
        hints = _extract_semantic_hints(analysis_text)
        final_vibe_score = _compute_final_vibe_score(
            lyric_score, audio_vibe_score, hints, audio_features
        )
        final_sentiment = _label_from_score(final_vibe_score, lyric_result["scores"])
        adjusted_scores = _build_adjusted_scores(
            lyric_result["scores"], lyric_score, final_vibe_score
        )

        print(
            "  [hybrid] "
            f"lyric={lyric_score:+.2f} audio={audio_vibe_score:+.2f} "
            f"final={final_vibe_score:+.2f} -> {final_sentiment}"
        )

        results.append(
            {
                "track_id": track["track_id"],
                "name": track["name"],
                "artist": track["artist"],
                "album": track.get("album", ""),
                "popularity": track.get("popularity", 0),
                "duration_ms": track.get("duration_ms", 0),
                "sentiment": final_sentiment,
                "scores": adjusted_scores,
                "detected_language": lang_code,
                "preprocessing_stats": prep_stats,
                "lyric_sentiment": lyric_result["sentiment"],
                "lyric_scores": lyric_result["scores"],
                "lyric_score": lyric_score,
                "audio_vibe_score": audio_vibe_score,
                "vibe_score": final_vibe_score,
                "semantic_hints": hints,
                "audio_features": audio_features,
            }
        )

    return results
