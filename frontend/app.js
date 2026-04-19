/**
 * app.js — VibeCheck Spotify Sentiment Analyzer
 * Maneja: formulario, llamada a API, render de charts interactivos y song cards
 */

'use strict';

// ─── Configuración ────────────────────────────────────────────────────────────
// IMPORTANTE: Reemplazar con la URL de tu API Gateway después del deploy
const API_URL = 'https://lunzatfoxb.execute-api.us-east-1.amazonaws.com/analyze';

// Para pruebas locales sin API, usar datos mock
const USE_MOCK = false;

const MOCK_DATA = {
  playlist: {
    name: "Today's Top Hits",
    owner: "Spotify",
    image_url: "https://i.scdn.co/image/ab67706f00000002e4eadd417a05b2f31c99bed8",
    total_tracks: 50,
    description: "Ed Sheeran is on top of the Hottest 50!"
  },
  summary: {
    total: 20,
    dominant: "POSITIVE",
    counts:      { POSITIVE: 13, NEUTRAL: 5, NEGATIVE: 2 },
    percentages: { POSITIVE: 65.0, NEUTRAL: 25.0, NEGATIVE: 10.0 },
    weighted_score: 0.42,
    vibe_label: "😊 Positiva"
  },
  tracks: [
    { name:"Flowers", artist:"Miley Cyrus", sentiment:"POSITIVE", scores:{Positive:.88,Neutral:.08,Negative:.04,Mixed:0}, popularity:95 },
    { name:"Anti-Hero", artist:"Taylor Swift", sentiment:"NEUTRAL", scores:{Positive:.35,Neutral:.55,Negative:.1,Mixed:0}, popularity:92 },
    { name:"As It Was", artist:"Harry Styles", sentiment:"POSITIVE", scores:{Positive:.78,Neutral:.15,Negative:.07,Mixed:0}, popularity:90 },
    { name:"Shakira: Bzrp Music Sessions #53", artist:"Bizarrap", sentiment:"NEGATIVE", scores:{Positive:.12,Neutral:.18,Negative:.7,Mixed:0}, popularity:88 },
    { name:"Unholy", artist:"Sam Smith", sentiment:"NEUTRAL", scores:{Positive:.3,Neutral:.6,Negative:.1,Mixed:0}, popularity:87 },
    { name:"Creepin'", artist:"Metro Boomin", sentiment:"NEGATIVE", scores:{Positive:.08,Neutral:.2,Negative:.72,Mixed:0}, popularity:85 },
    { name:"Golden Hour", artist:"JVKE", sentiment:"POSITIVE", scores:{Positive:.91,Neutral:.05,Negative:.04,Mixed:0}, popularity:84 },
    { name:"Rich Flex", artist:"Drake", sentiment:"POSITIVE", scores:{Positive:.62,Neutral:.28,Negative:.10,Mixed:0}, popularity:89 },
    { name:"Calm Down", artist:"Rema & Selena Gomez", sentiment:"POSITIVE", scores:{Positive:.80,Neutral:.12,Negative:.08,Mixed:0}, popularity:91 },
    { name:"I'm Good (Blue)", artist:"David Guetta", sentiment:"POSITIVE", scores:{Positive:.85,Neutral:.10,Negative:.05,Mixed:0}, popularity:86 },
    { name:"Lift Me Up", artist:"Rihanna", sentiment:"NEUTRAL", scores:{Positive:.40,Neutral:.50,Negative:.10,Mixed:0}, popularity:83 },
    { name:"Cruel Summer", artist:"Taylor Swift", sentiment:"POSITIVE", scores:{Positive:.72,Neutral:.20,Negative:.08,Mixed:0}, popularity:94 },
    { name:"Escapism.", artist:"RAYE", sentiment:"NEUTRAL", scores:{Positive:.35,Neutral:.50,Negative:.15,Mixed:0}, popularity:80 },
    { name:"Die For You", artist:"The Weeknd", sentiment:"POSITIVE", scores:{Positive:.68,Neutral:.22,Negative:.10,Mixed:0}, popularity:88 },
    { name:"Ella Baila Sola", artist:"Eslabon Armado", sentiment:"NEUTRAL", scores:{Positive:.42,Neutral:.45,Negative:.13,Mixed:0}, popularity:82 },
    { name:"Boy's a liar Pt. 2", artist:"PinkPantheress", sentiment:"POSITIVE", scores:{Positive:.66,Neutral:.24,Negative:.10,Mixed:0}, popularity:81 },
    { name:"La Bebe (Remix)", artist:"Yng Lvcas", sentiment:"POSITIVE", scores:{Positive:.60,Neutral:.30,Negative:.10,Mixed:0}, popularity:79 },
    { name:"Quevedo: Bzrp Music Sessions #52", artist:"Bizarrap", sentiment:"POSITIVE", scores:{Positive:.55,Neutral:.35,Negative:.10,Mixed:0}, popularity:85 },
    { name:"Star Walkin'", artist:"Lil Nas X", sentiment:"POSITIVE", scores:{Positive:.70,Neutral:.20,Negative:.10,Mixed:0}, popularity:78 },
    { name:"Bloody Mary", artist:"Lady Gaga", sentiment:"NEGATIVE", scores:{Positive:.10,Neutral:.15,Negative:.75,Mixed:0}, popularity:77 },
  ],
  png_url: null
};

// ─── Elementos del DOM ────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const heroSection     = $('hero');
const loadingSection  = $('loading');
const resultsSection  = $('results');
const form            = $('analyze-form');
const urlInput        = $('playlist-url');
const maxTracksSelect = $('max-tracks');
const analyzeBtn      = $('analyze-btn');
const demoBtn         = $('demo-btn');
const errorToast      = $('error-toast');
const errorMsg        = $('error-msg');
const newAnalysisBtn  = $('new-analysis-btn');
const downloadBtn     = $('download-btn');
const filterTabs      = document.querySelectorAll('.filter-tab');

// Chart instances (para destruir antes de re-renderizar)
let gaugeChartInstance = null;
let donutChartInstance = null;

// Datos actuales (para filtros)
let currentTracks = [];

// ─── Demo / URL de prueba ─────────────────────────────────────────────────────
demoBtn.addEventListener('click', () => {
  urlInput.value = 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M';
  urlInput.focus();
});

// ─── Nueva búsqueda ───────────────────────────────────────────────────────────
newAnalysisBtn.addEventListener('click', () => {
  resultsSection.classList.add('hidden');
  heroSection.classList.remove('hidden');
  urlInput.value = '';
  urlInput.focus();
});

// ─── Filter tabs ──────────────────────────────────────────────────────────────
filterTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    filterTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    renderSongCards(currentTracks, tab.dataset.filter);
  });
});

// ─── Submit form ──────────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const playlistUrl = urlInput.value.trim();
  if (!playlistUrl) return;

  const maxTracks = parseInt(maxTracksSelect.value, 10);

  setLoading(true);

  try {
    let data;

    if (USE_MOCK) {
      // Simular delay de API
      await simulateLoadingSteps();
      data = MOCK_DATA;
    } else {
      data = await callApi(playlistUrl, maxTracks);
    }

    renderResults(data);
  } catch (err) {
    console.error('Error:', err);
    showError(err.message || 'Error al analizar la playlist. Verificá la URL e intentá de nuevo.');
    setLoading(false);
  }
});

// ─── API Call ─────────────────────────────────────────────────────────────────
async function callApi(playlistUrl, maxTracks) {
  // Paso 1
  setStep('step-spotify', 'active');

  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playlist_url: playlistUrl, max_tracks: maxTracks }),
  });

  // Paso 2
  setStep('step-spotify', 'done');
  setStep('step-comprehend', 'active');

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  const data = await res.json();

  // Paso 3
  setStep('step-comprehend', 'done');
  setStep('step-chart', 'active');
  await sleep(600); // pequeño delay para que se vea el paso
  setStep('step-chart', 'done');
  await sleep(400);

  return data;
}

// ─── Mock loading steps ───────────────────────────────────────────────────────
async function simulateLoadingSteps() {
  setStep('step-spotify', 'active');
  await sleep(1200);
  setStep('step-spotify', 'done');
  setStep('step-comprehend', 'active');
  await sleep(2000);
  setStep('step-comprehend', 'done');
  setStep('step-chart', 'active');
  await sleep(800);
  setStep('step-chart', 'done');
  await sleep(400);
}

// ─── Render Results ───────────────────────────────────────────────────────────
function renderResults(data) {
  const { playlist, summary, tracks, png_url } = data;
  currentTracks = tracks;

  // Playlist header
  const img = $('playlist-img');
  if (playlist.image_url) {
    img.src = playlist.image_url;
    img.style.display = 'block';
  } else {
    img.style.display = 'none';
  }
  $('playlist-name').textContent = playlist.name || 'Playlist';
  $('playlist-owner').textContent = playlist.owner || '';
  $('track-count').textContent = `${summary.total} canciones analizadas`;

  // Dominant badge
  const badge = $('dominant-badge');
  const domMap = {
    POSITIVE: { emoji: '🌟', text: summary.vibe_label, cls: '' },
    NEUTRAL:  { emoji: '😐', text: summary.vibe_label, cls: 'neutral' },
    NEGATIVE: { emoji: '😢', text: summary.vibe_label, cls: 'negative' },
  };
  const dom = domMap[summary.dominant] || domMap.NEUTRAL;
  $('dominant-emoji').textContent = dom.emoji;
  $('dominant-text').textContent  = dom.text;
  badge.className = `dominant-badge ${dom.cls}`;

  // Download button
  if (png_url) {
    downloadBtn.href = png_url;
    downloadBtn.style.display = 'flex';
  } else {
    downloadBtn.style.display = 'none';
  }

  // Charts
  renderGauge(summary.weighted_score, summary.vibe_label);
  renderDonut(summary.percentages, summary.counts);
  renderStats(summary);
  renderSongCards(tracks, 'ALL');

  // Show results, hide loading
  setLoading(false);
  loadingSection.classList.add('hidden');
  heroSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  // Reset filter tabs
  filterTabs.forEach(t => t.classList.remove('active'));
  filterTabs[0].classList.add('active');
}

// ─── Gauge Chart (Speedometer) ────────────────────────────────────────────────
function renderGauge(score, label) {
  if (gaugeChartInstance) gaugeChartInstance.destroy();

  // score: -1.0 a +1.0  →  convertir a porcentaje del gauge (0-100)
  const pct = ((score + 1) / 2) * 100;  // 0% = muy negativo, 100% = muy positivo
  const clampedPct = Math.max(0, Math.min(100, pct));

  const negPct     = Math.max(0, 33 - clampedPct / 3);
  const neuPct     = 34;
  const posPct     = Math.min(100, clampedPct / 3 + 33) - 66;

  // Color de la aguja según score
  const needleColor = score > 0.2 ? '#1DB954'
                    : score < -0.2 ? '#E8645A'
                    : '#9a9a9a';

  const ctx = document.getElementById('gaugeChart').getContext('2d');

  // Datos del gauge: rojo | gris | verde (semicírculo superior)
  gaugeChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [33.3, 33.4, 33.3],
        backgroundColor: [
          'rgba(232,100,90,0.85)',
          'rgba(83,83,83,0.7)',
          'rgba(29,185,84,0.85)',
        ],
        borderWidth: 0,
        borderRadius: 4,
        circumference: 180,
        rotation: 270,
      }, {
        // Aguja: un punto pequeño en la posición correcta
        data: [clampedPct, 100 - clampedPct],
        backgroundColor: [needleColor, 'transparent'],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
        weight: 0.05,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend:    { display: false },
        tooltip:   { enabled: false },
        datalabels: {
          display: false,
        }
      },
      animation: {
        animateRotate: true,
        duration: 1000,
        easing: 'easeOutQuart',
      }
    }
  });

  // Actualizar texto central
  const scoreEl = $('gauge-score');
  const labelEl = $('gauge-label');
  scoreEl.textContent = (score >= 0 ? '+' : '') + score.toFixed(2);
  scoreEl.style.color = needleColor;
  if (labelEl) labelEl.textContent = label;
  $('gauge-label').textContent = label;
}

// ─── Donut Chart ──────────────────────────────────────────────────────────────
function renderDonut(percentages, counts) {
  if (donutChartInstance) donutChartInstance.destroy();

  const sentiments = ['POSITIVE', 'NEUTRAL', 'NEGATIVE'];
  const labels     = ['😊 Positiva', '😐 Neutral', '😢 Negativa'];
  const colors     = ['rgba(29,185,84,0.85)', 'rgba(83,83,83,0.75)', 'rgba(232,100,90,0.85)'];
  const borders    = ['#1DB954', '#535353', '#E8645A'];
  const data       = sentiments.map(s => percentages[s] || 0);

  Chart.register(ChartDataLabels);

  const ctx = document.getElementById('donutChart').getContext('2d');
  donutChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderColor: borders,
        borderWidth: 2,
        hoverOffset: 12,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed.toFixed(1)}% · ${counts[sentiments[ctx.dataIndex]] || 0} canciones`
          },
          backgroundColor: '#1A1A1A',
          borderColor: 'rgba(255,255,255,.1)',
          borderWidth: 1,
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,.7)',
          padding: 12,
        },
        datalabels: {
          color: '#fff',
          font: { weight: 'bold', size: 12 },
          formatter: (val) => val > 5 ? `${val.toFixed(0)}%` : '',
        }
      },
      animation: { animateRotate: true, duration: 1000, easing: 'easeOutQuart' }
    }
  });

  // Leyenda custom
  const legend = $('donut-legend');
  legend.innerHTML = sentiments.map((s, i) => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${borders[i]}"></div>
      <span>${labels[i]}: <strong>${(percentages[s] || 0).toFixed(1)}%</strong> (${counts[s] || 0})</span>
    </div>
  `).join('');
}

// ─── Stats Cards ───────────────────────────────────────────────────────────────
function renderStats(summary) {
  const { percentages, counts } = summary;
  const row = $('stats-row');
  const items = [
    { emoji: '😊', label: 'POSITIVAS', sentiment: 'POSITIVE', cls: 'positive' },
    { emoji: '😐', label: 'NEUTRAS',   sentiment: 'NEUTRAL',  cls: 'neutral' },
    { emoji: '😢', label: 'NEGATIVAS', sentiment: 'NEGATIVE', cls: 'negative' },
  ];
  row.innerHTML = items.map(({ emoji, label, sentiment, cls }) => `
    <div class="stat-card">
      <div class="stat-emoji">${emoji}</div>
      <div class="stat-value ${cls}">${(percentages[sentiment] || 0).toFixed(1)}%</div>
      <div class="stat-label">${label}</div>
      <div class="stat-count">${counts[sentiment] || 0} de ${summary.total} canciones</div>
    </div>
  `).join('');
}

// ─── Song Cards ───────────────────────────────────────────────────────────────
function renderSongCards(tracks, filter = 'ALL') {
  const grid = $('songs-grid');
  const filtered = filter === 'ALL' ? tracks
    : tracks.filter(t => t.sentiment === filter || (filter !== 'POSITIVE' && filter !== 'NEUTRAL' && filter !== 'NEGATIVE'));

  if (filtered.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;color:var(--white-30);padding:3rem;">
      No hay canciones ${filter === 'POSITIVE' ? 'positivas' : filter === 'NEGATIVE' ? 'negativas' : 'neutras'} en esta playlist.
    </div>`;
    return;
  }

  grid.innerHTML = filtered.map((t, i) => {
    const sentiment = t.sentiment === 'MIXED' ? 'NEUTRAL' : (t.sentiment || 'NEUTRAL');
    const chipLabel = { POSITIVE: '😊 Positivo', NEUTRAL: '😐 Neutral', NEGATIVE: '😢 Negativo', MIXED: '🔀 Mixto' }[t.sentiment] || 'Neutral';
    return `
    <div class="song-card" style="animation-delay:${Math.min(i * 0.03, 0.5)}s">
      <span class="song-num">${filtered.indexOf(t) + 1}</span>
      <div class="song-info">
        <div class="song-name" title="${escHtml(t.name)}">${escHtml(t.name)}</div>
        <div class="song-artist">${escHtml(t.artist)}</div>
      </div>
      <span class="sentiment-chip chip-${sentiment}">${chipLabel}</span>
    </div>`;
  }).join('');
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function setLoading(on) {
  analyzeBtn.disabled = on;
  analyzeBtn.classList.toggle('loading', on);
  analyzeBtn.querySelector('.btn-text').textContent = on ? 'Analizando…' : 'Analizar Playlist';

  if (on) {
    heroSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    // Reset step states
    ['step-spotify','step-comprehend','step-chart'].forEach(id => {
      const el = $(id);
      el.classList.remove('active','done');
    });
  } else {
    loadingSection.classList.add('hidden');
  }
}

function setStep(id, state) {
  const el = $(id);
  el.classList.remove('active','done');
  if (state) el.classList.add(state);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorToast.classList.remove('hidden');
  // Mostrar hero de nuevo
  heroSection.classList.remove('hidden');
  loadingSection.classList.add('hidden');
  setTimeout(() => errorToast.classList.add('hidden'), 6000);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ─── Auto-modo mock si no hay API configurada ─────────────────────────────────
if (!window.VIBECHECK_API_URL && !USE_MOCK) {
  console.warn('[VibeCheck] No se configuró VIBECHECK_API_URL. Usando datos mock para demo.');
  window.VIBECHECK_MOCK = true;
}
