/**
 * animations.js — VibeCheck Premium Interactions
 * Custom cursor, particles, GSAP scroll reveals, hover magnetic effects
 */

'use strict';

// ─── Wait for DOM ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initCursor();
  initParticles();
  initHeroAnimations();
  initScrollReveal();
});

// ─── GSAP Registration ────────────────────────────────────────────────────────
gsap.registerPlugin(ScrollTrigger);

// ═════════════════════════════════════════════════════════════════════════════
// CUSTOM CURSOR
// ═════════════════════════════════════════════════════════════════════════════
function initCursor() {
  const cursor   = document.getElementById('cursor');
  const follower = document.getElementById('cursor-follower');

  if (!cursor || !follower) return;

  // Hide on mobile
  if ('ontouchstart' in window) {
    cursor.style.display = 'none';
    follower.style.display = 'none';
    document.body.style.cursor = 'auto';
    document.querySelectorAll('button, a, input, select').forEach(el => {
      el.style.cursor = 'auto';
    });
    return;
  }

  let mouseX = -100, mouseY = -100;
  let followerX = -100, followerY = -100;
  let rafId;

  document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    gsap.to(cursor, { x: mouseX, y: mouseY, duration: 0.1, ease: 'power2.out' });
  });

  // Smooth follower
  function animateFollower() {
    followerX += (mouseX - followerX) * 0.12;
    followerY += (mouseY - followerY) * 0.12;
    gsap.set(follower, { x: followerX, y: followerY });
    rafId = requestAnimationFrame(animateFollower);
  }
  animateFollower();

  // Hover expand on interactive elements
  const interactable = document.querySelectorAll('button, a, input, select, .hint-url, .filter-tab, .song-card, .chart-card, .stat-card');
  interactable.forEach(el => {
    el.addEventListener('mouseenter', () => follower.classList.add('hovered'));
    el.addEventListener('mouseleave', () => follower.classList.remove('hovered'));
  });

  // Click animation
  document.addEventListener('mousedown', () => cursor.classList.add('clicked'));
  document.addEventListener('mouseup',   () => cursor.classList.remove('clicked'));
}

// ═════════════════════════════════════════════════════════════════════════════
// PARTICLE CANVAS
// ═════════════════════════════════════════════════════════════════════════════
function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  let width, height;
  let animFrame;

  function resize() {
    width  = canvas.width  = canvas.offsetWidth;
    height = canvas.height = canvas.offsetHeight;
  }

  window.addEventListener('resize', resize);
  resize();

  class Particle {
    constructor() { this.reset(); }

    reset() {
      this.x  = Math.random() * width;
      this.y  = Math.random() * height;
      this.vx = (Math.random() - .5) * .3;
      this.vy = (Math.random() - .5) * .3;
      this.alpha   = Math.random() * .3 + .04;
      this.radius  = Math.random() * 1.2 + .3;  // máx 1.5px — evita el círculo grande
      this.green   = Math.random() > .8;
      this.twinkle = Math.random() * Math.PI * 2;
    }

    update() {
      this.x += this.vx;
      this.y += this.vy;
      this.twinkle += .02;
      if (this.x < 0 || this.x > width || this.y < 0 || this.y > height) this.reset();
    }

    draw() {
      const pulse = Math.sin(this.twinkle) * .2;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
      if (this.green) {
        ctx.fillStyle = `rgba(29,185,84,${this.alpha + pulse})`;
      } else {
        ctx.fillStyle = `rgba(248,248,248,${this.alpha + pulse})`;
      }
      ctx.fill();
    }
  }

  // Spawn particles
  const COUNT = Math.min(80, Math.floor((width * height) / 18000));
  for (let i = 0; i < COUNT; i++) particles.push(new Particle());

  // Draw connections
  function drawConnections() {
    const maxDist = 130;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx   = particles[i].x - particles[j].x;
        const dy   = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < maxDist) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(29,185,84,${(1 - dist / maxDist) * .05})`;
          ctx.lineWidth = .8;
          ctx.stroke();
        }
      }
    }
  }

  function loop() {
    ctx.clearRect(0, 0, width, height);
    particles.forEach(p => { p.update(); p.draw(); });
    drawConnections();
    animFrame = requestAnimationFrame(loop);
  }
  loop();
}

// ═════════════════════════════════════════════════════════════════════════════
// HERO ENTRANCE ANIMATIONS
// ═════════════════════════════════════════════════════════════════════════════
function initHeroAnimations() {
  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

  tl.to('.reveal-fade.logo-wrap', {
    opacity: 1,
    duration: .8,
    delay: .2,
  })
  .to('.headline-line:nth-child(1)', {
    opacity: 1,
    y: 0,
    duration: .9,
  }, '-=.4')
  .to('.headline-line:nth-child(2)', {
    opacity: 1,
    y: 0,
    duration: .9,
  }, '-=.65')
  .to('.hero-sub.reveal-fade', {
    opacity: 1,
    duration: .8,
  }, '-=.5');
}

// ═════════════════════════════════════════════════════════════════════════════
// SCROLL REVEAL (for Results section)
// ═════════════════════════════════════════════════════════════════════════════
function initScrollReveal() {
  // Called externally after results render
  window.animateResultsIn = function () {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    // Header
    tl.from('.results-header', {
      opacity: 0,
      y: 30,
      duration: .7,
    })
    // Charts
    .from('.chart-card', {
      opacity: 0,
      y: 40,
      stagger: .15,
      duration: .7,
    }, '-=.3')
    // Stat cards
    .from('.stats-row', {
      opacity: 0,
      y: 30,
      duration: .6,
    }, '-=.2')
    // Songs header
    .from('.songs-header', {
      opacity: 0,
      y: 20,
      duration: .5,
    }, '-=.15')
    // Song cards staggered
    .from('.song-card', {
      opacity: 0,
      y: 16,
      stagger: { amount: .6, from: 'start' },
      duration: .4,
    }, '-=.1')
    // Actions
    .from('.actions-row', {
      opacity: 0,
      y: 20,
      duration: .5,
    }, '-=.1');
  };

  // Song card re-render animation
  window.animateSongCards = function () {
    const cards = document.querySelectorAll('.song-card');
    if (!cards.length) return;
    gsap.killTweensOf(cards);
    gsap.fromTo(cards,
      { opacity: 0, y: 14 },
      {
        opacity: 1, y: 0,
        stagger: { amount: .45, from: 'start' },
        duration: .38,
        ease: 'power2.out',
      }
    );
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// MAGNETIC BUTTON EFFECT (hero analyze button)
// ═════════════════════════════════════════════════════════════════════════════
(function initMagneticBtn() {
  const btn = document.getElementById('analyze-btn');
  if (!btn || 'ontouchstart' in window) return;

  btn.addEventListener('mousemove', e => {
    const rect   = btn.getBoundingClientRect();
    const cx     = rect.left + rect.width  / 2;
    const cy     = rect.top  + rect.height / 2;
    const dx     = (e.clientX - cx) * .28;
    const dy     = (e.clientY - cy) * .28;
    gsap.to(btn, { x: dx, y: dy, duration: .35, ease: 'power2.out' });
  });

  btn.addEventListener('mouseleave', () => {
    gsap.to(btn, { x: 0, y: 0, duration: .6, ease: 'elastic.out(1,.4)' });
  });
})();

// ═════════════════════════════════════════════════════════════════════════════
// COUNTER ANIMATION (stat values)
// ═════════════════════════════════════════════════════════════════════════════
window.animateCounter = function (el, targetValue, suffix = '%', duration = 1200) {
  const startTime = performance.now();
  const start = 0;

  function tick(now) {
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + (targetValue - start) * eased;
    el.textContent = current.toFixed(1) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
};

// ═════════════════════════════════════════════════════════════════════════════
// GAUGE SCORE COUNT-UP
// ═════════════════════════════════════════════════════════════════════════════
window.animateGaugeScore = function (el, targetScore, duration = 1000) {
  const startTime  = performance.now();
  const prefix     = targetScore >= 0 ? '+' : '';

  function tick(now) {
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    const current  = targetScore * eased;
    el.textContent = (current >= 0 ? '+' : '') + current.toFixed(2);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
};
