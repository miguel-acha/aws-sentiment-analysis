"""
aggregator.py
-------------
Agrega resultados del analisis track por track.

Usa preferentemente `vibe_score` y el `sentiment` final ajustado del pipeline
hibrido (letra + senales musicales), con fallback a los scores clasicos.
"""


def _sentiment_to_score(track_or_scores: dict) -> float:
    if "vibe_score" in track_or_scores:
        return round(track_or_scores.get("vibe_score", 0.0), 4)

    scores = track_or_scores.get("scores", track_or_scores)
    return round(scores.get("Positive", 0.0) - scores.get("Negative", 0.0), 4)


def _get_vibe_label(score: float) -> str:
    if score >= 0.55:
        return "Euforico"
    if score >= 0.30:
        return "Radiante"
    if score >= 0.08:
        return "Fiestero"
    if score >= -0.05:
        return "Equilibrado"
    if score >= -0.25:
        return "Melancolico"
    if score >= -0.50:
        return "Introspectivo"
    return "Sombrio"


def _generate_ai_interpretation(dominant: str, vibe_label: str, percentages: dict) -> str:
    if dominant == "POSITIVE":
        return (
            f"El analisis hibrido detecta una vibra {vibe_label.lower()}, "
            f"con {percentages['POSITIVE']}% de tracks en energia positiva o bailable."
        )
    if dominant == "NEGATIVE":
        return (
            f"La playlist cae hacia un tono {vibe_label.lower()}, con "
            f"{percentages['NEGATIVE']}% de tracks mas tensos, oscuros o introspectivos."
        )
    if dominant == "MIXED":
        return (
            f"Predomina una mezcla emocional compleja. La playlist suena {vibe_label.lower()}, "
            "pero alterna entre impulso, tension y contraste."
        )
    return (
        f"La coleccion se siente {vibe_label.lower()}, con un balance importante de tracks "
        f"neutros ({percentages['NEUTRAL']}%) y cambios suaves de energia."
    )


def aggregate(analyzed_tracks: list[dict]) -> dict:
    sentiments = ("POSITIVE", "NEUTRAL", "NEGATIVE", "MIXED")

    if not analyzed_tracks:
        return {
            "total": 0,
            "dominant": "NEUTRAL",
            "counts": {s: 0 for s in sentiments},
            "percentages": {s: 0.0 for s in sentiments},
            "weighted_score": 0.0,
            "average_track_score": 0.0,
            "sentiment_balance": 0.0,
            "vibe_label": "Sin datos",
            "ai_interpretation": "No hay suficientes canciones para interpretar esta playlist.",
            "tracks_by_sentiment": {s: [] for s in sentiments},
        }

    counts = {s: 0 for s in sentiments}
    tracks_by_sentiment = {s: [] for s in sentiments}
    total_weighted_score = 0.0

    for track in analyzed_tracks:
        sentiment = track.get("sentiment", "NEUTRAL")
        if sentiment not in counts:
            sentiment = "NEUTRAL"

        counts[sentiment] += 1
        tracks_by_sentiment[sentiment].append(track)
        total_weighted_score += _sentiment_to_score(track)

    total = len(analyzed_tracks)
    average_track_score = round(total_weighted_score / total, 4)
    percentages = {key: round((value / total) * 100, 1) for key, value in counts.items()}
    dominant = max(counts, key=lambda key: counts[key])
    sentiment_balance = round((counts["POSITIVE"] - counts["NEGATIVE"]) / total, 4)
    weighted_score = round(
        max(-1.0, min(1.0, average_track_score * 0.65 + sentiment_balance * 0.35)),
        4,
    )
    vibe_label = _get_vibe_label(weighted_score)
    ai_interpretation = _generate_ai_interpretation(dominant, vibe_label, percentages)

    return {
        "total": total,
        "dominant": dominant,
        "counts": counts,
        "percentages": percentages,
        "weighted_score": weighted_score,
        "average_track_score": average_track_score,
        "sentiment_balance": sentiment_balance,
        "vibe_label": vibe_label,
        "ai_interpretation": ai_interpretation,
        "tracks_by_sentiment": tracks_by_sentiment,
    }
