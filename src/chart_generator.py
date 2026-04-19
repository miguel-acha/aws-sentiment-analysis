"""
chart_generator.py
------------------
Genera las visualizaciones del reporte:
  1. Vibe Gauge (velocímetro) con matplotlib polar
  2. Donut Chart de distribución de sentimientos
  3. PNG combinado (gauge + donut) para subir a S3

Tema: Spotify dark (#000000 / #1DB954)
"""

import io
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Backend sin display (necesario en Lambda)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from PIL import Image

# ─── Paleta de colores Spotify dark ──────────────────────────────────────────
BG_COLOR    = "#0A0A0A"
CARD_COLOR  = "#121212"
GREEN       = "#1DB954"
RED         = "#E8645A"
GRAY        = "#535353"
LIGHT_GRAY  = "#B3B3B3"
WHITE       = "#FFFFFF"

SENTIMENT_COLORS = {
    "POSITIVE": GREEN,
    "NEUTRAL":  GRAY,
    "NEGATIVE": RED,
}


def _inches_fig(w_px: int, h_px: int, dpi: int = 150) -> tuple[float, float]:
    return w_px / dpi, h_px / dpi


# ─── 1. VIBE GAUGE ───────────────────────────────────────────────────────────

def render_gauge(weighted_score: float, vibe_label: str) -> bytes:
    """
    Genera el velocímetro como PNG en bytes.
    weighted_score: float entre -1.0 y +1.0
    """
    fig = plt.figure(figsize=_inches_fig(600, 340), facecolor=BG_COLOR)
    ax  = fig.add_subplot(111, projection="polar")
    ax.set_facecolor(BG_COLOR)

    # El gauge va de 180° (izq, -1.0) a 0° (der, +1.0) → media dona superior
    theta_min = 0        # radianes, pi = 180°
    theta_max = math.pi

    # ── Arco de fondo ──────────────────────────────────────────────────────
    n_segments = 300
    thetas = np.linspace(theta_min, theta_max, n_segments)
    # Gradiente rojo → gris → verde
    for i in range(n_segments - 1):
        t_mid = (thetas[i] + thetas[i + 1]) / 2
        # t=0 → right (positive), t=pi → left (negative)
        frac = t_mid / math.pi  # 0=positivo, 1=negativo
        r = min(1.0, 2 * frac)           # 0→0.5: rojo sube
        g = GREEN_FRAC = min(1.0, 2 * (1 - frac))  # 0.5→1: verde baja
        b = 0.2
        color = (r * 0.91, g * 0.72, b)  # mezcla RGB
        if frac < 0.5:
            color = (g * 0.35, g * 0.35, g * 0.35 + 0.2)   # gris→gris
        if frac >= 0.5:
            color = (0.91, g * 0.39, 0.36)  # hacia rojo
        else:
            color = (g * 0.11, g * 0.73, g * 0.33)  # hacia verde
        ax.fill_between(
            [thetas[i], thetas[i + 1]], 0.65, 0.95,
            color=color, zorder=1,
        )

    # ── Aguja ───────────────────────────────────────────────────────────────
    # score de -1→+1 mapeado a ángulo pi→0
    needle_angle = math.pi * (1 - (weighted_score + 1) / 2)
    ax.annotate(
        "",
        xy=(needle_angle, 0.88),
        xytext=(needle_angle, 0.05),
        arrowprops=dict(arrowstyle="-|>", color=WHITE, lw=2.5,
                        mutation_scale=18),
        zorder=5,
    )
    # Centro (punto)
    ax.plot(needle_angle, 0.05, "o", color=WHITE, ms=7, zorder=6)

    # ── Labels ─────────────────────────────────────────────────────────────
    ax.text(math.pi, 0.45, "😢\nDepresiva", ha="center", va="center",
            color=RED, fontsize=8, fontweight="bold")
    ax.text(math.pi / 2, 1.18, "😐 Neutral", ha="center", va="center",
            color=LIGHT_GRAY, fontsize=8)
    ax.text(0, 0.45, "🌟\nPositiva", ha="center", va="center",
            color=GREEN, fontsize=8, fontweight="bold")

    # Score text en el centro
    ax.text(math.pi / 2, 0.35, f"{weighted_score:+.2f}",
            ha="center", va="center", color=WHITE,
            fontsize=22, fontweight="bold",
            transform=ax.transData)
    ax.text(math.pi / 2, 0.15, vibe_label,
            ha="center", va="center", color=LIGHT_GRAY,
            fontsize=9, transform=ax.transData)

    # ── Estética ────────────────────────────────────────────────────────────
    ax.set_xlim(0, math.pi)
    ax.set_ylim(0, 1.2)
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(-1)
    ax.axis("off")

    plt.title("VIBE METER", color=WHITE, fontsize=12,
              fontweight="bold", pad=10)
    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=BG_COLOR)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─── 2. DONUT CHART ──────────────────────────────────────────────────────────

def render_donut(percentages: dict, counts: dict) -> bytes:
    """Genera el donut chart de distribución de sentimientos."""
    fig, ax = plt.subplots(figsize=_inches_fig(500, 400), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    labels   = ["POSITIVE", "NEUTRAL", "NEGATIVE"]
    sizes    = [percentages.get(l, 0) for l in labels]
    colors   = [SENTIMENT_COLORS[l] for l in labels]
    emojis   = {"POSITIVE": "😊", "NEUTRAL": "😐", "NEGATIVE": "😢"}

    # Filtrar segmentos vacíos
    non_zero = [(s, c, l) for s, c, l in zip(sizes, colors, labels) if s > 0]
    if not non_zero:
        non_zero = [(100, GRAY, "NEUTRAL")]

    sizes_filt  = [x[0] for x in non_zero]
    colors_filt = [x[1] for x in non_zero]
    labels_filt = [x[2] for x in non_zero]

    wedges, _ = ax.pie(
        sizes_filt,
        colors=colors_filt,
        startangle=90,
        wedgeprops=dict(width=0.55, edgecolor=BG_COLOR, linewidth=3),
        counterclock=False,
    )

    # Etiquetas exteriores
    for wedge, label, size in zip(wedges, labels_filt, sizes_filt):
        angle = (wedge.theta2 + wedge.theta1) / 2
        x = 1.25 * math.cos(math.radians(angle))
        y = 1.25 * math.sin(math.radians(angle))
        ha = "center"
        ax.annotate(
            f"{emojis[label]} {label}\n{size:.1f}%  ({counts.get(label, 0)} canciones)",
            xy=(x * 0.85, y * 0.85),
            xytext=(x, y),
            fontsize=8,
            color=WHITE,
            ha=ha,
            va="center",
            arrowprops=dict(arrowstyle="-", color=LIGHT_GRAY, lw=0.8),
        )

    # Texto central
    ax.text(0, 0, "VIBE\nDISTRIBUCIÓN", ha="center", va="center",
            color=WHITE, fontsize=10, fontweight="bold")

    ax.set_title("Distribución de Sentimientos", color=WHITE,
                 fontsize=12, fontweight="bold", pad=15)
    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=BG_COLOR,
                bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─── 3. COMBINED PNG ─────────────────────────────────────────────────────────

def generate_report_png(
    analyzed_tracks: list[dict],
    summary: dict,
    playlist_info: dict,
) -> bytes:
    """
    Genera el PNG combinado del reporte completo:
    Header + Gauge + Donut + Top songs list
    """
    gauge_bytes  = render_gauge(summary["weighted_score"], summary["vibe_label"])
    donut_bytes  = render_donut(summary["percentages"], summary["counts"])

    gauge_img = Image.open(io.BytesIO(gauge_bytes))
    donut_img = Image.open(io.BytesIO(donut_bytes))

    # Canvas final
    W = 1200
    H = 700
    canvas = Image.new("RGB", (W, H), color=(10, 10, 10))

    # Header text via matplotlib
    fig_header, ax_h = plt.subplots(figsize=(W / 150, 0.8), facecolor=BG_COLOR)
    ax_h.axis("off")
    ax_h.text(0.02, 0.5, f"🎵 {playlist_info.get('name', 'Playlist')}",
              transform=ax_h.transAxes, fontsize=14, fontweight="bold",
              color=WHITE, va="center")
    ax_h.text(0.98, 0.5,
              f"{summary['total']} canciones · Vibe: {summary['vibe_label']}",
              transform=ax_h.transAxes, fontsize=10,
              color=GREEN, va="center", ha="right")
    buf_h = io.BytesIO()
    fig_header.savefig(buf_h, format="png", dpi=150, facecolor=BG_COLOR,
                       bbox_inches="tight")
    plt.close(fig_header)
    buf_h.seek(0)
    header_img = Image.open(buf_h)

    # Resize y pegar
    header_resized = header_img.resize((W, 60))
    gauge_resized  = gauge_img.resize((580, 310))
    donut_resized  = donut_img.resize((580, 330))

    canvas.paste(header_resized, (0, 0))
    canvas.paste(gauge_resized, (20, 70))
    canvas.paste(donut_resized, (610, 60))

    # Footer
    fig_footer, ax_f = plt.subplots(figsize=(W / 150, 0.5), facecolor=BG_COLOR)
    ax_f.axis("off")
    ax_f.text(0.5, 0.5, "Generado con Amazon Comprehend · Spotify Web API",
              transform=ax_f.transAxes, fontsize=8,
              color=LIGHT_GRAY, va="center", ha="center")
    buf_f = io.BytesIO()
    fig_footer.savefig(buf_f, format="png", dpi=150, facecolor=BG_COLOR,
                       bbox_inches="tight")
    plt.close(fig_footer)
    buf_f.seek(0)
    footer_img = Image.open(buf_f).resize((W, 40))
    canvas.paste(footer_img, (0, H - 40))

    # Exportar PNG final
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    out.seek(0)
    return out.read()
