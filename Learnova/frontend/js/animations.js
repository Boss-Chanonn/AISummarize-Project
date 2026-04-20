/* ── Learnova Premium Animations ── */

/* Page transition */
(function() {
  const overlay = document.createElement('div');
  overlay.id = 'page-transition';
  document.body.appendChild(overlay);

  /* Fade in on load */
  overlay.classList.add('out');
  requestAnimationFrame(() => {
    requestAnimationFrame(() => { overlay.style.transition = 'opacity 0.3s'; overlay.classList.remove('out'); });
  });

  /* Fade out on navigation */
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('javascript') || a.target === '_blank') return;
    if (href.startsWith('http')) return;
    e.preventDefault();
    overlay.classList.add('out');
    setTimeout(() => { window.location.href = href; }, 260);
  });
})();

/* Scroll-reveal: IntersectionObserver */
(function() {
  if (!window.IntersectionObserver) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  function observe() {
    document.querySelectorAll('.reveal:not(.visible)').forEach(el => io.observe(el));
  }
  observe();
  /* Re-observe after dynamic content */
  const mo = new MutationObserver(observe);
  mo.observe(document.body, { childList: true, subtree: true });
})();

/* Number count-up for stat cards */
function countUp(el, target, duration, suffix) {
  const start = performance.now();
  const isDecimal = target % 1 !== 0;
  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); /* ease-out cubic */
    const current = isDecimal ? (target * ease).toFixed(0) : Math.round(target * ease);
    el.textContent = current + (suffix || '');
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

function initCountUp() {
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target = parseFloat(el.dataset.target);
    const suffix = el.dataset.suffix || '';
    const io = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        countUp(el, target, 900, suffix);
        io.disconnect();
      }
    }, { threshold: 0.5 });
    io.observe(el);
  });
}

/* History items staggered entrance */
function animateHistoryItems() {
  document.querySelectorAll('.history-item-anim').forEach((el, i) => {
    el.style.animationDelay = (i * 0.06) + 's';
  });
}

function addRipple(target, x, y) {
  const rect = target.getBoundingClientRect();
  const ripple = document.createElement('span');
  ripple.className = 'ui-ripple';
  const size = Math.max(rect.width, rect.height) * 1.25;
  ripple.style.width = size + 'px';
  ripple.style.height = size + 'px';
  ripple.style.left = (x - rect.left) + 'px';
  ripple.style.top = (y - rect.top) + 'px';
  target.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove(), { once: true });
}

function initButtonRipple() {
  document.addEventListener('pointerdown', e => {
    const el = e.target.closest('.btn, .sched-btn, .quiz-opt');
    if (!el) return;
    addRipple(el, e.clientX, e.clientY);
  });
}

function swapPanelContent(container, html, direction = 'forward') {
  const current = container.firstElementChild;
  if (!current) {
    container.innerHTML = html;
    const next = container.firstElementChild;
    if (next) {
      next.classList.add('panel-stage', direction === 'forward' ? 'enter-forward' : 'enter-backward');
      requestAnimationFrame(() => next.classList.add('is-active'));
    }
    return;
  }

  const minHeight = container.offsetHeight;
  container.style.minHeight = minHeight + 'px';
  current.classList.add('panel-stage', direction === 'forward' ? 'exit-forward' : 'exit-backward');
  requestAnimationFrame(() => current.classList.add('is-exiting'));

  setTimeout(() => {
    container.innerHTML = html;
    const next = container.firstElementChild;
    if (next) {
      next.classList.add('panel-stage', direction === 'forward' ? 'enter-forward' : 'enter-backward');
      requestAnimationFrame(() => next.classList.add('is-active'));
    }
    setTimeout(() => { container.style.minHeight = ''; }, 320);
  }, 170);
}

function revealSequence(targets, baseDelay = 90) {
  const items = Array.isArray(targets) ? targets : Array.from(targets);
  items.forEach((node, index) => {
    if (!node) return;
    setTimeout(() => node.classList.add('visible'), baseDelay * index);
  });
}

function setModalSourceFromEvent(event) {
  const source = event && event.currentTarget
    ? event.currentTarget.closest('.history-item') || event.currentTarget.closest('.btn, .qa-card, .sched-btn, .quiz-opt') || event.currentTarget
    : null;
  window.__lnModalSource = source;
  if (event) event.stopPropagation();
}

function animateModalFromSource(box) {
  const source = window.__lnModalSource;
  if (!box || !source) return;
  const sourceRect = source.getBoundingClientRect();
  const boxRect = box.getBoundingClientRect();
  const scaleX = Math.max(sourceRect.width / boxRect.width, 0.78);
  const scaleY = Math.max(sourceRect.height / boxRect.height, 0.32);
  const translateX = sourceRect.left + (sourceRect.width / 2) - (boxRect.left + (boxRect.width / 2));
  const translateY = sourceRect.top + (sourceRect.height / 2) - (boxRect.top + (boxRect.height / 2));
  box.animate([
    { transform: `translate(${translateX}px, ${translateY}px) scale(${scaleX}, ${scaleY})`, opacity: 0.72, filter: 'blur(6px)' },
    { transform: 'translate(0, 0) scale(1, 1)', opacity: 1, filter: 'blur(0px)' }
  ], {
    duration: 320,
    easing: 'cubic-bezier(0.16,1,0.3,1)'
  });
  window.__lnModalSource = null;
}

/* Magnetic tilt on qa-cards (subtle, Apple-like) */
function initTilt() {
  document.querySelectorAll('.qa-card, .stat-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `translateY(-2px) rotateX(${-y * 3}deg) rotateY(${x * 3}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
      card.style.transition = 'transform 0.4s cubic-bezier(0.16,1,0.3,1), border-color 0.18s, box-shadow 0.22s';
      setTimeout(() => { card.style.transition = ''; }, 400);
    });
    card.addEventListener('mouseenter', () => { card.style.transition = 'none'; });
  });
}

/* Smooth score ring draw */
function animateScoreRing(svgCircle, pct) {
  if (!svgCircle) return;
  const circ = 251.2;
  const target = circ - (pct / 100) * circ;
  svgCircle.style.strokeDasharray = circ;
  svgCircle.style.strokeDashoffset = circ; /* start at 0% */
  svgCircle.style.transition = 'none';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      svgCircle.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.16,1,0.3,1)';
      svgCircle.style.strokeDashoffset = target;
    });
  });
}

/* Progress bar animated fill */
function animateProgressBars() {
  document.querySelectorAll('.prog-fill[data-width]').forEach(bar => {
    const width = bar.dataset.width;
    bar.style.width = '0';
    const io = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        setTimeout(() => {
          bar.style.transition = 'width 0.9s cubic-bezier(0.16,1,0.3,1)';
          bar.style.width = width;
        }, 200);
        io.disconnect();
      }
    }, { threshold: 0.5 });
    io.observe(bar);
  });
}

/* Sidebar active item indicator animation */
function animateSidebarActive() {
  const active = document.querySelector('.sidebar-item.active');
  if (!active) return;
  active.style.animation = 'none';
  active.style.opacity = '0';
  active.style.transform = 'translateX(-6px)';
  setTimeout(() => {
    active.style.transition = 'opacity 0.3s, transform 0.4s cubic-bezier(0.16,1,0.3,1)';
    active.style.opacity = '';
    active.style.transform = '';
  }, 80);
}

/* Input focus glow */
function initInputGlow() {
  document.querySelectorAll('.input').forEach(input => {
    input.addEventListener('focus', () => {
      input.style.transition = 'border-color 0.18s, box-shadow 0.25s cubic-bezier(0.16,1,0.3,1)';
    });
  });
}

function choreographPageLoad() {
  document.querySelectorAll('.sidebar-item').forEach((item, index) => {
    item.style.opacity = '0';
    item.style.transform = 'translateX(-10px)';
    item.style.animation = 'slideRight 0.38s cubic-bezier(0.16,1,0.3,1) forwards';
    item.style.animationDelay = `${0.04 * index}s`;
  });
  document.querySelectorAll('.page-header, .stats-grid, .quick-actions, .res-list, #history-list, #recent-activity-list').forEach((section, index) => {
    if (!section.classList.contains('fade-up')) {
      section.style.animation = `fadeUp 0.42s cubic-bezier(0.16,1,0.3,1) both`;
      section.style.animationDelay = `${0.06 * index}s`;
    }
  });
}

/* Smooth open/close for mini-results in history */
function smoothToggle(el, open) {
  if (open) {
    el.style.display = 'block';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-6px)';
    el.style.transition = 'opacity 0.25s, transform 0.35s cubic-bezier(0.16,1,0.3,1)';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; });
    });
  } else {
    el.style.transition = 'opacity 0.18s, transform 0.22s';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-4px)';
    setTimeout(() => { el.style.display = 'none'; }, 220);
  }
}

/* Run everything on DOM ready */
document.addEventListener('DOMContentLoaded', () => {
  initCountUp();
  initTilt();
  initInputGlow();
  initButtonRipple();
  choreographPageLoad();
  animateHistoryItems();
  animateProgressBars();
  setTimeout(animateSidebarActive, 100);
});

/* Export for inline use */
window.LN = { countUp, animateScoreRing, smoothToggle, animateProgressBars, swapPanelContent, revealSequence, setModalSourceFromEvent, animateModalFromSource };
