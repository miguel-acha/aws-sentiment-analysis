"""
aggregator.py
-------------
Recibe la lista de canciones analizadas y calcula:
- Conteo por sentimiento (POSITIVE / NEUTRAL / NEGATIVE)
- Porcentajes
- Score ponderado (-1.0 a +1.0) para el velocímetro
- Sentimiento dominante
"""


def _sentiment_to_score(scores: dict) -> float:
    """
    Convierte los scores de Comprehend a un valor escalar entre -1.0 y +1.0.
    Fórmula: positive - negative (ignorando neutral y mixed)
    """
    return round(scores.get("Positive", 0) - scores.get("Negative", 0), 4)


def aggregate(analyzed_tracks: list[dict]) -> dict:
    """
    Agrega los resultados del análisis de sentimiento.

    Args:
        analyzed_tracks: Lista de dicts con { sentiment, scores, ... }

    Returns:
        Dict con {
            total, dominant, counts, percentages,
            weighted_score, vibe_label, tracks_by_sentiment
        }
    """
    if not analyzed_tracks:
        return {
            "total": 0,
            "dominant": "NEUTRAL",
            "counts": {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0},
            "percentages": {"POSITIVE": 0.0, "NEUTRAL": 0.0, "NEGATIVE": 0.0},
            "weighted_score": 0.0,
            "vibe_label": "Sin datos",
            "tracks_by_sentiment": {"POSITIVE": [], "NEUTRAL": [], "NEGATIVE": []},
        }

    counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}
    tracks_by_sentiment = {"POSITIVE": [], "NEUTRAL": [], "NEGATIVE": []}
    total_weighted_score = 0.0

    for track in analyzed_tracks:
        sentiment = track.get("sentiment", "NEUTRAL")

        # MIXED → mapeamos al sentimiento con mayor score
        if sentiment == "MIXED":
            scores = track.get("scores", {})
            sentiment = max(
                ["POSITIVE", "NEGATIVE", "NEUTRAL"],
                key=lambda s: scores.get(s.capitalize(), 0),
            )

        counts[sentiment] = counts.get(sentiment, 0) + 1
        tracks_by_sentiment[sentiment].append(track)
        total_weighted_score += _sentiment_to_score(track.get("scores", {}))

    total = len(analyzed_tracks)
    weighted_score = round(total_weighted_score / total, 4) if total > 0 else 0.0

    percentages = {
        k: round((v / total) * 100, 1) for k, v in counts.items()
    }

    # Sentimiento dominante (el que más canciones tiene)
    dominant = max(counts, key=lambda k: counts[k])

    # Etiqueta de vibe basada en el score ponderado
    vibe_label = _get_vibe_label(weighted_score)

    return {
        "total": total,
        "dominant": dominant,
        "counts": counts,
        "percentages": percentages,
        "weighted_score": weighted_score,
        "vibe_label": vibe_label,
        "tracks_by_sentiment": tracks_by_sentiment,
    }


def _get_vibe_label(score: float) -> str:
    """Convierte el score ponderado a una etiqueta de vibe descriptiva."""
    if score >= 0.5:
        return "🌟 Muy Positiva"
    elif score >= 0.2:
        return "😊 Positiva"
    elif score >= -0.2:
        return "😐 Neutral"
    elif score >= -0.5:
        return "😔 Melancólica"
    else:
        return "😢 Muy Negativa"


if __name__ == "__main__":
    # Test con datos mock
    mock = [
        {"name": "Happy", "artist": "Pharrell", "sentiment": "POSITIVE", "scores": {"Positive": 0.95, "Negative": 0.01, "Neutral": 0.04, "Mixed": 0.0}},
        {"name": "Creep", "artist": "Radiohead", "sentiment": "NEGATIVE", "scores": {"Positive": 0.02, "Negative": 0.90, "Neutral": 0.08, "Mixed": 0.0}},
        {"name": "Blinding Lights", "artist": "The Weeknd", "sentiment": "POSITIVE", "scores": {"Positive": 0.80, "Negative": 0.05, "Neutral": 0.15, "Mixed": 0.0}},
        {"name": "Hurt", "artist": "NIN", "sentiment": "NEGATIVE", "scores": {"Positive": 0.01, "Negative": 0.95, "Neutral": 0.04, "Mixed": 0.0}},
        {"name": "Shape of You", "artist": "Ed Sheeran", "sentiment": "NEUTRAL", "scores": {"Positive": 0.45, "Negative": 0.10, "Neutral": 0.45, "Mixed": 0.0}},
    ]
    result = aggregate(mock)
    print(f"Total: {result['total']}")
    print(f"Dominante: {result['dominant']}")
    print(f"Porcentajes: {result['percentages']}")
    print(f"Score ponderado: {result['weighted_score']}")
    print(f"Vibe: {result['vibe_label']}")
