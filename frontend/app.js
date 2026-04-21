/**
 * app.js — VibeCheck Spotify Sentiment Analyzer v3.0
 * Maneja: formulario, llamada a API, render de charts interactivos y song cards
 */

'use strict';

// ─── Configuración ────────────────────────────────────────────────────────────
const API_URL = 'https://lunzatfoxb.execute-api.us-east-1.amazonaws.com/analyze';

// ─── PKCE Config & Auth ───────────────────────────────────────────────────────
const SPOTIFY_CLIENT_ID = '3f9d449a2ca24dcab6456ecad92e055c';
const SPOTIFY_REDIRECT_URI = 'https://main.d3i36ughrz7z5g.amplifyapp.com/';
let spotifyAccessToken = sessionStorage.getItem('spotify_access_token');
let spotifyUserProfile = null;
let spotifyUserPlaylists = [];

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
    counts: { POSITIVE: 13, NEUTRAL: 5, NEGATIVE: 2 },
    percentages: { POSITIVE: 65.0, NEUTRAL: 25.0, NEGATIVE: 10.0 },
    weighted_score: 0.42,
    vibe_label: "Positiva"
  },
  tracks: [
    { name: "Flowers", artist: "Miley Cyrus", sentiment: "POSITIVE", scores: { Positive: .88, Neutral: .08, Negative: .04, Mixed: 0 }, popularity: 95 },
    { name: "Anti-Hero", artist: "Taylor Swift", sentiment: "NEUTRAL", scores: { Positive: .35, Neutral: .55, Negative: .1, Mixed: 0 }, popularity: 92 },
    { name: "As It Was", artist: "Harry Styles", sentiment: "POSITIVE", scores: { Positive: .78, Neutral: .15, Negative: .07, Mixed: 0 }, popularity: 90 },
    { name: "Shakira: Bzrp Music Sessions #53", artist: "Bizarrap", sentiment: "NEGATIVE", scores: { Positive: .12, Neutral: .18, Negative: .7, Mixed: 0 }, popularity: 88 },
    { name: "Unholy", artist: "Sam Smith", sentiment: "NEUTRAL", scores: { Positive: .3, Neutral: .6, Negative: .1, Mixed: 0 }, popularity: 87 },
    { name: "Creepin'", artist: "Metro Boomin", sentiment: "NEGATIVE", scores: { Positive: .08, Neutral: .2, Negative: .72, Mixed: 0 }, popularity: 85 },
    { name: "Golden Hour", artist: "JVKE", sentiment: "POSITIVE", scores: { Positive: .91, Neutral: .05, Negative: .04, Mixed: 0 }, popularity: 84 },
    { name: "Rich Flex", artist: "Drake", sentiment: "POSITIVE", scores: { Positive: .62, Neutral: .28, Negative: .10, Mixed: 0 }, popularity: 89 },
    { name: "Calm Down", artist: "Rema & Selena Gomez", sentiment: "POSITIVE", scores: { Positive: .80, Neutral: .12, Negative: .08, Mixed: 0 }, popularity: 91 },
    { name: "I'm Good (Blue)", artist: "David Guetta", sentiment: "POSITIVE", scores: { Positive: .85, Neutral: .10, Negative: .05, Mixed: 0 }, popularity: 86 },
    { name: "Lift Me Up", artist: "Rihanna", sentiment: "NEUTRAL", scores: { Positive: .40, Neutral: .50, Negative: .10, Mixed: 0 }, popularity: 83 },
    { name: "Cruel Summer", artist: "Taylor Swift", sentiment: "POSITIVE", scores: { Positive: .72, Neutral: .20, Negative: .08, Mixed: 0 }, popularity: 94 },
    { name: "Escapism.", artist: "RAYE", sentiment: "NEUTRAL", scores: { Positive: .35, Neutral: .50, Negative: .15, Mixed: 0 }, popularity: 80 },
    { name: "Die For You", artist: "The Weeknd", sentiment: "POSITIVE", scores: { Positive: .68, Neutral: .22, Negative: .10, Mixed: 0 }, popularity: 88 },
    { name: "Ella Baila Sola", artist: "Eslabon Armado", sentiment: "NEUTRAL", scores: { Positive: .42, Neutral: .45, Negative: .13, Mixed: 0 }, popularity: 82 },
    { name: "Boy's a liar Pt. 2", artist: "PinkPantheress", sentiment: "POSITIVE", scores: { Positive: .66, Neutral: .24, Negative: .10, Mixed: 0 }, popularity: 81 },
    { name: "La Bebe (Remix)", artist: "Yng Lvcas", sentiment: "POSITIVE", scores: { Positive: .60, Neutral: .30, Negative: .10, Mixed: 0 }, popularity: 79 },
    { name: "Quevedo: Bzrp Music Sessions #52", artist: "Bizarrap", sentiment: "POSITIVE", scores: { Positive: .55, Neutral: .35, Negative: .10, Mixed: 0 }, popularity: 85 },
    { name: "Star Walkin'", artist: "Lil Nas X", sentiment: "POSITIVE", scores: { Positive: .70, Neutral: .20, Negative: .10, Mixed: 0 }, popularity: 78 },
    { name: "Bloody Mary", artist: "Lady Gaga", sentiment: "NEGATIVE", scores: { Positive: .10, Neutral: .15, Negative: .75, Mixed: 0 }, popularity: 77 },
  ],
  png_url: null
};

// ─── DOM ───────────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const heroSection = $('hero');
const authSection = $('auth-section');
const analyzeSection = $('analyze-section');
const spotifyLoginBtn = $('spotify-login-btn');
const loadingSection = $('loading');
const resultsSection = $('results');
const form = $('analyze-form');
const urlInput = $('playlist-url');
const maxTracksSelect = $('max-tracks');
const analyzeBtn = $('analyze-btn');
const demoBtn = $('demo-btn');
const errorToast = $('error-toast');
const errorMsg = $('error-msg');
const newAnalysisBtn = $('new-analysis-btn');
const downloadBtn = $('download-btn');
const filterTabs = document.querySelectorAll('.filter-tab');
const userBar = $('user-bar');
const userAvatarImg = $('user-avatar');
const userAvatarInitials = $('user-avatar-initials');
const userDisplayName = $('user-display-name');
const logoutBtn = $('logout-btn');
const playlistsGrid = $('playlists-grid');
const refreshPlaylistsBtn = $('refresh-playlists-btn');

// ─── Rebind cursor hover ───────────────────────────────────────────────────────
function rebindCursorHover() {
  const follower = document.getElementById('cursor-follower');
  if (!follower) return;
  document.querySelectorAll('.song-card, .stat-card, .chart-card').forEach(el => {
    el.addEventListener('mouseenter', () => follower.classList.add('hovered'));
    el.addEventListener('mouseleave', () => follower.classList.remove('hovered'));
  });
}

let gaugeChartInstance = null;
let donutChartInstance = null;
let currentTracks = [];

// ─── Demo btn ─────────────────────────────────────────────────────────────────
if (demoBtn) {
  demoBtn.addEventListener('click', () => {
    if (urlInput) urlInput.value = 'https://open.spotify.com/playlist/1BmqpSfccNZMPtkMpIl2FZ';
    if (form) form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  });
}

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

// ─── PKCE Auth ────────────────────────────────────────────────────────────────
function generateRandomString(length) {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  for (let i = 0; i < length; i++) text += possible.charAt(Math.floor(Math.random() * possible.length));
  return text;
}

async function generateCodeChallenge(codeVerifier) {
  const data = new TextEncoder().encode(codeVerifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode.apply(null, [...new Uint8Array(digest)]))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function handleSpotifyLogin() {
  const verifier = generateRandomString(128);
  const challenge = await generateCodeChallenge(verifier);
  sessionStorage.setItem('spotify_code_verifier', verifier);

  const params = new URLSearchParams({
    client_id: SPOTIFY_CLIENT_ID,
    response_type: 'code',
    redirect_uri: SPOTIFY_REDIRECT_URI,
    code_challenge_method: 'S256',
    code_challenge: challenge,
    scope: 'playlist-read-private playlist-read-collaborative user-read-private user-read-email',
  });
  window.location.href = `https://accounts.spotify.com/authorize?${params.toString()}`;
}

async function handleSpotifyCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  if (!code) return;

  const verifier = sessionStorage.getItem('spotify_code_verifier');
  if (!verifier) return;

  const loginBtn = spotifyLoginBtn;
  if (loginBtn) { loginBtn.disabled = true; loginBtn.querySelector('.btn-text').textContent = 'Autenticando...'; }

  try {
    const body = new URLSearchParams({
      client_id: SPOTIFY_CLIENT_ID,
      grant_type: 'authorization_code',
      code,
      redirect_uri: SPOTIFY_REDIRECT_URI,
      code_verifier: verifier,
    });

    const res = await fetch('https://accounts.spotify.com/api/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });

    if (!res.ok) throw new Error('Error al intercambiar el código OAuth');

    const data = await res.json();
    spotifyAccessToken = data.access_token;
    sessionStorage.setItem('spotify_access_token', spotifyAccessToken);

    window.history.replaceState({}, document.title, window.location.pathname);
    sessionStorage.removeItem('spotify_code_verifier');
  } catch (err) {
    console.error('Auth error:', err);
    showError('Error al autenticar con Spotify. Intentá de nuevo.');
    if (loginBtn) { loginBtn.disabled = false; loginBtn.querySelector('.btn-text').textContent = 'Conectar con Spotify'; }
  }
}

function updateAuthUI() {
  heroSection.classList.remove('hidden');
  loadingSection.classList.add('hidden');
  updateUserBar();
  if (spotifyAccessToken || USE_MOCK) {
    authSection.classList.add('hidden');
    analyzeSection.classList.remove('hidden');
    renderPlaylists();
  } else {
    authSection.classList.remove('hidden');
    analyzeSection.classList.add('hidden');
  }
}

function updateUserBar() {
  if (!userBar) return;
  if (spotifyAccessToken && spotifyUserProfile) {
    userBar.classList.add('active');
    document.body.classList.add('has-user-bar');
    const name = spotifyUserProfile.display_name || spotifyUserProfile.id || 'Usuario';
    if (userDisplayName) userDisplayName.textContent = name;
    const avatarUrl = spotifyUserProfile.images?.length > 0
      ? spotifyUserProfile.images[spotifyUserProfile.images.length > 1 ? 1 : 0].url
      : null;
    if (avatarUrl) {
      if (userAvatarImg) { userAvatarImg.src = avatarUrl; userAvatarImg.style.display = 'block'; }
      if (userAvatarInitials) userAvatarInitials.style.display = 'none';
    } else {
      if (userAvatarImg) userAvatarImg.style.display = 'none';
      if (userAvatarInitials) {
        userAvatarInitials.textContent = name.charAt(0).toUpperCase();
        userAvatarInitials.style.display = 'flex';
      }
    }
  } else {
    userBar.classList.remove('active');
    document.body.classList.remove('has-user-bar');
  }
}

async function fetchSpotifyUserData() {
  if (!spotifyAccessToken) return;
  try {
    const profileRes = await fetch('https://api.spotify.com/v1/me', {
      headers: { Authorization: `Bearer ${spotifyAccessToken}` }
    });
    if (!profileRes.ok) {
      console.warn('[VibeCheck] Token inválido o expirado.');
      spotifyAccessToken = null;
      sessionStorage.removeItem('spotify_access_token');
      return;
    }
    spotifyUserProfile = await profileRes.json();

    const plRes = await fetch('https://api.spotify.com/v1/me/playlists?limit=50', {
      headers: { Authorization: `Bearer ${spotifyAccessToken}` }
    });
    if (plRes.ok) {
      const plData = await plRes.json();
      spotifyUserPlaylists = plData.items || [];
    }
  } catch (err) {
    console.error('[VibeCheck] Error obteniendo datos de Spotify:', err);
  }
}

function renderPlaylists() {
  if (!playlistsGrid) return;
  const playlists = spotifyUserPlaylists;

  if (!playlists || playlists.length === 0) {
    playlistsGrid.innerHTML = '<p class="playlists-empty">No se encontraron playlists en tu cuenta.</p>';
    return;
  }

  playlistsGrid.innerHTML = playlists.map(pl => {
    const imgUrl = pl.images?.length > 0 ? pl.images[0].url : '';
    const name = pl.name || 'Sin nombre';
    const tracks = pl.tracks ? pl.tracks.total : '—';
    const url = pl.external_urls?.spotify || '';
    return `
      <div class="playlist-card" data-url="${url}" role="button" tabindex="0" aria-label="Analizar ${escHtml(name)}">
        <div class="playlist-card-img-wrap">
          ${imgUrl
        ? `<img src="${imgUrl}" alt="${escHtml(name)}" class="playlist-card-img" loading="lazy" />`
        : `<div class="playlist-card-no-img"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg></div>`
      }
          <div class="playlist-card-overlay">
            <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M5 3l14 9-14 9V3z"/></svg>
          </div>
        </div>
        <div class="playlist-card-name" title="${escHtml(name)}">${escHtml(name)}</div>
        <div class="playlist-card-tracks">${tracks} canciones</div>
      </div>`;
  }).join('');

  playlistsGrid.querySelectorAll('.playlist-card').forEach(card => {
    const handler = () => {
      const url = card.dataset.url;
      if (!url) return;
      playlistsGrid.querySelectorAll('.playlist-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      if (urlInput) urlInput.value = url;
      if (form) form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); } });
  });
}

if (spotifyLoginBtn) spotifyLoginBtn.addEventListener('click', handleSpotifyLogin);

if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    spotifyAccessToken = null;
    spotifyUserProfile = null;
    spotifyUserPlaylists = [];
    sessionStorage.removeItem('spotify_access_token');
    sessionStorage.removeItem('spotify_code_verifier');
    updateAuthUI();
    if (!resultsSection.classList.contains('hidden')) {
      resultsSection.classList.add('hidden');
      heroSection.classList.remove('hidden');
    }
  });
}

if (refreshPlaylistsBtn) {
  refreshPlaylistsBtn.addEventListener('click', async () => {
    if (!spotifyAccessToken) return;
    refreshPlaylistsBtn.style.animation = 'spin360 .6s linear';
    if (playlistsGrid) playlistsGrid.innerHTML = '<div class="playlists-loading">Actualizando...</div>';
    await fetchSpotifyUserData();
    renderPlaylists();
    setTimeout(() => { refreshPlaylistsBtn.style.animation = ''; }, 700);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  handleSpotifyCallback().then(async () => {
    if (spotifyAccessToken) await fetchSpotifyUserData();
    updateAuthUI();
  });
});

// ─── API Call ─────────────────────────────────────────────────────────────────
async function callApi(playlistUrl, maxTracks) {
  setStep('step-spotify', 'active');

  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playlist_url: playlistUrl, max_tracks: maxTracks, spotify_token: spotifyAccessToken }),
  });

  setStep('step-spotify', 'done');
  setStep('step-comprehend', 'active');

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }

  const data = await res.json();

  setStep('step-comprehend', 'done');
  setStep('step-chart', 'active');
  await sleep(600);
  setStep('step-chart', 'done');
  await sleep(400);

  return data;
}

async function simulateLoadingSteps() {
  setStep('step-spotify', 'active'); await sleep(1200);
  setStep('step-spotify', 'done');
  setStep('step-comprehend', 'active'); await sleep(2000);
  setStep('step-comprehend', 'done');
  setStep('step-chart', 'active'); await sleep(800);
  setStep('step-chart', 'done'); await sleep(400);
}

// ─── Render Results ───────────────────────────────────────────────────────────
function renderResults(data) {
  const { playlist, summary, tracks, png_url } = data;
  currentTracks = tracks;

  // ── Cover art ──
  const imgEl = $('playlist-img');
  if (playlist.image_url) {
    imgEl.src = playlist.image_url;
    imgEl.style.display = 'block';

    // Blurred background in intro banner
    const introBg = $('results-intro-bg');
    if (introBg) {
      introBg.style.backgroundImage = `url(${playlist.image_url})`;
      // Trigger fade-in after paint
      requestAnimationFrame(() => {
        requestAnimationFrame(() => introBg.classList.add('loaded'));
      });
    }
  } else {
    imgEl.style.display = 'none';
  }

  // ── Playlist info ──
  $('playlist-name').textContent = playlist.name || 'Playlist';
  $('playlist-owner').textContent = playlist.owner || '';
  $('track-count').textContent = `${summary.total} canciones analizadas`;

  // ── AI Interpretation ──
  const aiTextEl = $('ai-interpretation-text');
  if (aiTextEl) {
    if (summary.ai_interpretation) {
      aiTextEl.textContent = summary.ai_interpretation;
    } else {
      aiTextEl.textContent = "El algoritmo de IA ha escaneado la vibra de esta playlist.";
    }
  }

  // ── Vibe pill (formerly dominant-badge) ──
  const badge = $('dominant-badge');
  const vibeLabel = summary.vibe_label
    ? summary.vibe_label.replace(/[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, '').trim()
    : summary.dominant;

  const badgeIcons = {
    POSITIVE: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>',
    NEUTRAL: '<circle cx="12" cy="12" r="10"/><path d="M8 12h8"/>',
    NEGATIVE: '<path d="M12 22a10 10 0 100-20 10 10 0 000 20z"/><path d="M16 16s-1.5-2-4-2-4 2-4 2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
    MIXED: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  };
  const dom = badgeIcons[summary.dominant] ? summary.dominant : 'NEUTRAL';
  const badgeIconEl = $('badge-icon');
  if (badgeIconEl) badgeIconEl.innerHTML = badgeIcons[dom];
  $('dominant-text').textContent = vibeLabel;
  // Update pill class — maps to .vibe-pill-lg.positive / .negative / etc.
  badge.className = `vibe-pill-lg ${dom.toLowerCase()}`;

  // ── Download button ──
  downloadBtn.style.display = 'flex';
  const oldHandler = downloadBtn._dlHandler;
  if (oldHandler) downloadBtn.removeEventListener('click', oldHandler);
  downloadBtn._dlHandler = async (e) => {
    e.preventDefault();
    if (typeof html2canvas !== 'undefined') {
      try {
        const origHTML = downloadBtn.innerHTML;
        downloadBtn.innerHTML = 'Generando...';
        const canvas = await html2canvas(resultsSection, {
          backgroundColor: '#060608', scale: 2, useCORS: true, logging: false,
        });
        const link = document.createElement('a');
        link.download = `vibe-${(playlist.name || 'reporte').replace(/\s+/g, '-').toLowerCase()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
        downloadBtn.innerHTML = origHTML;
      } catch { showError('No se pudo generar el reporte.'); }
    } else if (png_url) {
      window.open(png_url, '_blank');
    } else {
      showError('Descarga no disponible en este navegador.');
    }
  };
  downloadBtn.addEventListener('click', downloadBtn._dlHandler);

  // ── Show results section FIRST so charts can measure dimensions ──
  setLoading(false);
  loadingSection.classList.add('hidden');
  heroSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  // ── Render charts & cards ──
  renderGauge(summary.weighted_score, summary.vibe_label);
  renderDonut(summary.percentages, summary.counts);
  renderStats(summary);
  renderSongCards(tracks, 'ALL', true);

  // ── Reset filter tabs ──
  filterTabs.forEach(t => t.classList.remove('active'));
  filterTabs[0].classList.add('active');

  // ── Entry animations ──
  if (typeof window.animateResultsIn === 'function') window.animateResultsIn();

  rebindCursorHover();
}

// ─── Gauge Chart ──────────────────────────────────────────────────────────────
function renderGauge(score, label) {
  if (gaugeChartInstance) gaugeChartInstance.destroy();

  const pct = ((score + 1) / 2) * 100;
  const p = Math.max(0, Math.min(100, pct));
  const needleColor = score > 0.15 ? '#1DB954' : score < -0.15 ? '#E8645A' : '#7B9CC0';

  const ctx = document.getElementById('gaugeChart').getContext('2d');

  gaugeChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [p, 100 - p],
        backgroundColor: [needleColor, 'rgba(255,255,255,0.05)'],
        borderWidth: 0,
        borderRadius: [10, 0],
        circumference: 180,
        rotation: 270,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 2,
      cutout: '74%',
      events: [],
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
        datalabels: { display: false },
      },
      animation: { animateRotate: true, duration: 1600, easing: 'easeOutExpo' },
    }
  });

  // Update score in the intro banner (IDs moved there in HTML)
  const scoreEl = $('gauge-score');
  const labelEl = $('gauge-label');
  if (scoreEl) scoreEl.style.color = needleColor;
  const cleanLabel = label ? label.replace(/[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, '').trim() : '—';
  // gauge-label stays "Vibe Score" as set in HTML — don't overwrite it with cleanLabel
  // but animate the number:
  if (typeof window.animateGaugeScore === 'function') {
    window.animateGaugeScore(scoreEl, score);
  } else if (scoreEl) {
    scoreEl.textContent = (score >= 0 ? '+' : '') + score.toFixed(2);
  }
}

// ─── Donut Chart ──────────────────────────────────────────────────────────────
function renderDonut(percentages, counts) {
  if (donutChartInstance) donutChartInstance.destroy();

  const ALL = [
    { key: 'POSITIVE', label: 'Positiva', color: 'rgba(29,185,84,0.9)', border: '#1DB954' },
    { key: 'NEUTRAL', label: 'Neutral', color: 'rgba(100,122,172,0.85)', border: '#7B9CC0' },
    { key: 'NEGATIVE', label: 'Negativa', color: 'rgba(232,100,90,0.9)', border: '#E8645A' },
    { key: 'MIXED', label: 'Mixta', color: 'rgba(245,166,35,0.85)', border: '#F5A623' },
  ];
  const active = ALL.filter(s => (percentages[s.key] || 0) > 0);

  Chart.register(ChartDataLabels);
  const ctx = document.getElementById('donutChart').getContext('2d');

  donutChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: active.map(s => s.label),
      datasets: [{
        data: active.map(s => percentages[s.key] || 0),
        backgroundColor: active.map(s => s.color),
        borderColor: active.map(s => s.border),
        borderWidth: 2,
        hoverOffset: 14,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '78%',
      layout: { padding: 4 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(8,8,14,.98)',
          borderColor: 'rgba(255,255,255,.06)',
          borderWidth: 1,
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,.75)',
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: ctx => {
              const s = active[ctx.dataIndex];
              const c = counts[s.key] || 0;
              return ` ${s.label}: ${(percentages[s.key] || 0).toFixed(1)}%  ·  ${c} pista${c !== 1 ? 's' : ''}`;
            }
          }
        },
        datalabels: { display: false },
      },
      animation: { animateRotate: true, animateScale: true, duration: 1400, easing: 'easeOutExpo' },
    }
  });

  // ── Legend — cleaner layout ──
  const legend = $('donut-legend');
  legend.innerHTML = active.map(s => {
    const pct = (percentages[s.key] || 0).toFixed(1);
    const c = counts[s.key] || 0;
    return `
      <div class="legend-item" role="listitem">
        <div class="legend-item-left">
          <div class="legend-dot" style="background:${s.border};box-shadow:0 0 6px ${s.border}55;"></div>
          <span>${s.label}</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="legend-pct">${pct}%</span>
          <span class="legend-count">${c}</span>
        </div>
      </div>`;
  }).join('');
}

// ─── Stats Cards ──────────────────────────────────────────────────────────────
function renderStats(summary) {
  const { percentages, counts, total } = summary;
  const row = $('stats-row');

  const ITEMS = [
    { label: 'Positivas', key: 'POSITIVE', cls: 'positive', color: '#1DB954' },
    { label: 'Neutras', key: 'NEUTRAL', cls: 'neutral', color: '#7B9CC0' },
    { label: 'Negativas', key: 'NEGATIVE', cls: 'negative', color: '#E8645A' },
    { label: 'Mixtas', key: 'MIXED', cls: 'mixed', color: '#F5A623' },
  ].filter(item => (counts[item.key] || 0) > 0);

  row.innerHTML = ITEMS.map(({ label, key, cls, color }) => {
    const pct = (percentages[key] || 0).toFixed(1);
    const count = counts[key] || 0;
    return `
    <div class="stat-card ${cls}" role="listitem">
      <div class="stat-value" style="color:${color}" data-target="${pct}">0%</div>
      <div class="stat-label">${label}</div>
      <div class="stat-count">${count} de ${total}</div>
      <div class="progress-bg">
        <div class="progress-fill" data-width="${pct}"
             style="background:${color};box-shadow:0 0 8px ${color}44;"></div>
      </div>
    </div>`;
  }).join('');

  requestAnimationFrame(() => {
    row.querySelectorAll('.stat-value[data-target]').forEach(el => {
      const t = parseFloat(el.dataset.target);
      if (typeof window.animateCounter === 'function') window.animateCounter(el, t, '%');
      else el.textContent = t.toFixed(1) + '%';
    });
    setTimeout(() => {
      row.querySelectorAll('.progress-fill[data-width]').forEach(el => {
        el.style.transition = 'width 1.2s cubic-bezier(0.4,0,0.2,1)';
        el.style.width = el.dataset.width + '%';
      });
    }, 80);
  });
}

// ─── Song Cards ───────────────────────────────────────────────────────────────
function renderSongCards(tracks, filter = 'ALL', isInit = false) {
  const grid = $('songs-grid');
  const filtered = filter === 'ALL' ? tracks : tracks.filter(t => t.sentiment === filter);

  if (filtered.length === 0) {
    const names = { POSITIVE: 'positivas', NEUTRAL: 'neutras', NEGATIVE: 'negativas', MIXED: 'mixtas' };
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;color:var(--white-25);padding:3rem;font-size:.88rem;">
        No hay canciones ${names[filter] || ''} en esta playlist.
      </div>`;
    return;
  }

  const chipLabel = { POSITIVE: 'Positivo', NEUTRAL: 'Neutral', NEGATIVE: 'Negativo', MIXED: 'Mixto' };

  grid.innerHTML = filtered.map((t, i) => {
    const chip = t.sentiment || 'NEUTRAL';
    const scores = t.scores || {};

    // Sentiment mini-bar — shows the three main confidence scores
    const pos = Math.round((scores.Positive || 0) * 100);
    const neu = Math.round((scores.Neutral || 0) * 100);
    const neg = Math.round((scores.Negative || 0) * 100);
    // Only show bar if we have score data
    const hasScores = pos + neu + neg > 0;
    const scoreBar = hasScores
      ? `<div class="song-score-bar" title="Positivo ${pos}% · Neutral ${neu}% · Negativo ${neg}%">
           <div class="bar-seg bar-pos" style="width:${pos}%"></div>
           <div class="bar-seg bar-neu" style="width:${neu}%"></div>
           <div class="bar-seg bar-neg" style="width:${neg}%"></div>
         </div>`
      : '';

    return `
    <div class="song-card" role="listitem">
      <span class="song-num">${i + 1}</span>
      <div class="song-info">
        <div class="song-name" title="${escHtml(t.name)}">${escHtml(t.name)}</div>
        <div class="song-artist">${escHtml(t.artist)}</div>
        ${scoreBar}
      </div>
      <span class="sentiment-chip chip-${chip}">${chipLabel[chip] || 'Neutral'}</span>
    </div>`;
  }).join('');

  if (typeof window.animateSongCards === 'function' && !isInit) {
    window.animateSongCards();
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function setLoading(on) {
  analyzeBtn.disabled = on;
  analyzeBtn.classList.toggle('loading', on);
  analyzeBtn.querySelector('.btn-text').textContent = on ? 'Analizando…' : 'Analizar';

  if (on) {
    heroSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    ['step-spotify', 'step-comprehend', 'step-chart'].forEach(id => {
      const el = $(id);
      el.classList.remove('active', 'done');
    });
  } else {
    loadingSection.classList.add('hidden');
  }
}

function setStep(id, state) {
  const el = $(id);
  el.classList.remove('active', 'done');
  if (state) el.classList.add(state);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorToast.classList.remove('hidden');
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