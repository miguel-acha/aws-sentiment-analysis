"""
aggregator.py
-------------
Agrega los resultados del análisis de sentimiento.

Cambios:
- MIXED se cuenta por separado (counts y percentages incluyen MIXED)
- dominant se calcula mapeando MIXED al sentimiento más cercano
- vibe_label expandido a 8 etiquetas descriptivas sin emojis
"""


def _sentiment_to_score(scores: dict) -> float:
    """Convierte los scores de Comprehend a escalar entre -1.0 y +1.0."""
    return round(scores.get("Positive", 0) - scores.get("Negative", 0), 4)


def _get_vibe_label(score: float) -> str:
    """Etiqueta descriptiva basada en el score ponderado (-1 a +1)."""
    if score >= 0.55:    return "Eufórico"
    elif score >= 0.30:  return "Radiante"
    elif score >= 0.10:  return "Optimista"
    elif score >= -0.10: return "Equilibrado"
    elif score >= -0.30: return "Melancólico"
    elif score >= -0.55: return "Introspectivo"
    else:                return "Sombrío"


def aggregate(analyzed_tracks: list) -> dict:
    """
    Agrega los resultados del análisis de sentimiento.

    Args:
        analyzed_tracks: Lista de dicts con { sentiment, scores, ... }

    Returns:
        Dict con { total, dominant, counts (incluye MIXED), percentages,
                   weighted_score, vibe_label, tracks_by_sentiment }
    """
    SENTIMENTS = ("POSITIVE", "NEUTRAL", "NEGATIVE", "MIXED")

    if not analyzed_tracks:
        return {
            "total": 0,
            "dominant": "NEUTRAL",
            "counts": {s: 0 for s in SENTIMENTS},
            "percentages": {s: 0.0 for s in SENTIMENTS},
            "weighted_score": 0.0,
            "vibe_label": "Sin datos",
            "tracks_by_sentiment": {s: [] for s in SENTIMENTS},
        }

    counts = {s: 0 for s in SENTIMENTS}
    tracks_by_sentiment = {s: [] for s in SENTIMENTS}
    total_weighted_score = 0.0

    # Para dominante, MIXED se mapea al sentimiento más cercano
    dominant_counts = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0}

    for track in analyzed_tracks:
        sentiment = track.get("sentiment", "NEUTRAL")
        if sentiment not in counts:
            sentiment = "NEUTRAL"

        counts[sentiment] += 1
        tracks_by_sentiment[sentiment].append(track)
        total_weighted_score += _sentiment_to_score(track.get("scores", {}))

        # Dominant: mapear MIXED al más alto
        if sentiment == "MIXED":
            raw_scores = track.get("scores", {})
            mapped = max(
                ["POSITIVE", "NEGATIVE", "NEUTRAL"],
                key=lambda s: raw_scores.get(s.capitalize(), 0),
            )
        else:
            mapped = sentiment
        dominant_counts[mapped] = dominant_counts.get(mapped, 0) + 1

    total = len(analyzed_tracks)
    weighted_score = round(total_weighted_score / total, 4) if total > 0 else 0.0
    percentages = {k: round((v / total) * 100, 1) for k, v in counts.items()}
    dominant = max(dominant_counts, key=lambda k: dominant_counts[k])
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


if __name__ == "__main__":
    mock = [
        {"name": "Happy",          "artist": "Pharrell",  "sentiment": "POSITIVE", "scores": {"Positive": 0.95, "Negative": 0.01, "Neutral": 0.04, "Mixed": 0.0}},
        {"name": "Creep",          "artist": "Radiohead", "sentiment": "NEGATIVE", "scores": {"Positive": 0.02, "Negative": 0.90, "Neutral": 0.08, "Mixed": 0.0}},
        {"name": "Blinding Lights","artist": "The Weeknd","sentiment": "POSITIVE", "scores": {"Positive": 0.80, "Negative": 0.05, "Neutral": 0.15, "Mixed": 0.0}},
        {"name": "Hurt",           "artist": "NIN",       "sentiment": "NEGATIVE", "scores": {"Positive": 0.01, "Negative": 0.95, "Neutral": 0.04, "Mixed": 0.0}},
        {"name": "Shape of You",   "artist": "Ed Sheeran","sentiment": "MIXED",    "scores": {"Positive": 0.45, "Negative": 0.35, "Neutral": 0.10, "Mixed": 0.10}},
    ]
    result = aggregate(mock)
    print(f"Total: {result['total']}")
    print(f"Dominante: {result['dominant']}")
    print(f"Counts: {result['counts']}")
    print(f"Porcentajes: {result['percentages']}")
    print(f"Score ponderado: {result['weighted_score']}")
    print(f"Vibe: {result['vibe_label']}")
