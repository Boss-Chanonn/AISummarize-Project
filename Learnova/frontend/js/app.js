/* ── Learnova shared JS ── */

/* ── User state (loaded from localStorage after login) ── */
const _storedUser = JSON.parse(localStorage.getItem('user') || 'null');
const LEARNOVA_USER = {
  name: (_storedUser && _storedUser.name) || 'User',
  initials: '',
  email: (_storedUser && _storedUser.email) || '',
  pendingEmail: '',
  avatarUrl: '',
  dob: '',
  phone: '',
  password: '',
  passwordMask: '•••••••',
  tier: (_storedUser && _storedUser.tier) || 'free',
  role: (_storedUser && _storedUser.role) || 'user',
};
LEARNOVA_USER.initials = getInitials(LEARNOVA_USER.name);

/* History is stored in localStorage (ln_history) — starts empty until user summarises */


function getHistoryItem(id) {
  const history = JSON.parse(localStorage.getItem('ln_history') || '[]');
  return history.find(item => item.id === id);
}

function getRecentActivity(limit = 5) {
  const history = JSON.parse(localStorage.getItem('ln_history') || '[]');
  return history.slice(0, limit);
}

function getResumeQuizUrl(id, mode = 'quiz') {
  return `upload.html?resume=${id}&mode=${mode}`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderSummaryMarkup(item, options = {}) {
  const ctaLabel = options.ctaLabel || (item.done ? 'Retake quiz →' : 'Continue to quiz →');
  const ctaHandler = options.ctaHandler || (item.done ? "window.location.href='upload.html'" : `window.location.href='${getResumeQuizUrl(item.id, 'quiz')}'`);
  const ctaHint = options.ctaHint || (item.done ? `${item.total} questions completed` : 'Summary ready to continue');
  const ctaBefore = options.ctaBefore || '';
  return `
    <div class="sum-header">
      <div class="sum-badge"><span class="sum-pulse"></span>AI summary</div>
      <div class="sum-pages">${escapeHtml(item.summary.pages)}</div>
    </div>
    <div class="sum-title">${escapeHtml(item.summary.title)}</div>
    <div class="sum-authors">${escapeHtml(item.summary.authors)}</div>
    <div class="sum-body">
      ${item.summary.body.map(paragraph => `<p>${escapeHtml(paragraph)}</p>`).join('')}
    </div>
    <div class="key-points">
      <div class="kp-label">Key takeaways</div>
      ${item.summary.takeaways.map(point => `<div class="kp-item"><span class="kp-dash">—</span>${escapeHtml(point)}</div>`).join('')}
    </div>
    <div class="quiz-cta">
      <div class="cta-hint">${ctaHint}</div>
      <button class="btn btn-primary" onclick="${ctaBefore}${ctaHandler}">${ctaLabel}</button>
    </div>
  `;
}

/* ── Theme / accessibility engine ── */
const THEMES = ['dark','light','high-contrast','deuteranopia','protanopia','tritanopia'];
const FONT_SIZES = ['default','large','xlarge'];

function applyTheme(t) {
  if (t === 'dark') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('ln_theme', t);
}
function applyFontSize(s) {
  if (s === 'default') document.documentElement.removeAttribute('data-fontsize');
  else document.documentElement.setAttribute('data-fontsize', s);
  localStorage.setItem('ln_fontsize', s);
}
function loadPrefs() {
  const t = localStorage.getItem('ln_theme') || 'dark';
  const s = localStorage.getItem('ln_fontsize') || 'default';
  applyTheme(t); applyFontSize(s);
}

function getInitials(name) {
  return String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0].toUpperCase())
    .join('') || 'U';
}

function getAvatarMarkup(size = 'default') {
  if (!LEARNOVA_USER.avatarUrl) return escapeHtml(LEARNOVA_USER.initials);
  return `<img src="${LEARNOVA_USER.avatarUrl}" alt="${escapeHtml(LEARNOVA_USER.name)}" class="avatar-image avatar-image-${size}">`;
}

/* ── Toast ── */
function showToast(msg, typeOrDuration, maybeDuration) {
  let type = '';
  let duration = 2800;

  if (typeof typeOrDuration === 'string') {
    type = typeOrDuration.toLowerCase();
    if (typeof maybeDuration === 'number') duration = maybeDuration;
  } else if (typeof typeOrDuration === 'number') {
    duration = typeOrDuration;
  }

  if (!type) {
    const low = String(msg || '').toLowerCase();
    type = /(fail|failed|error|unable|invalid|incorrect|wrong|denied|network|expired|missing)/.test(low)
      ? 'error'
      : 'success';
  }
  if (type !== 'success') type = 'error';

  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.className = 'toast';
    document.body.appendChild(t);
  }

  let icon = t.querySelector('.toast-icon');
  let msgEl = t.querySelector('#toast-msg');
  if (!icon || !msgEl) {
    t.innerHTML = '<div class="toast-icon" aria-hidden="true">&#10003;</div><span id="toast-msg"></span>';
    icon = t.querySelector('.toast-icon');
    msgEl = t.querySelector('#toast-msg');
  }

  icon.className = 'toast-icon ' + type;
  icon.innerHTML = type === 'success' ? '&#10003;' : '&#10005;';
  msgEl.textContent = msg;

  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), duration);
}

function syncUserUI() {
  const isPro = LEARNOVA_USER.tier === 'pro';
  document.querySelectorAll('.avatar-name').forEach(el => el.textContent = LEARNOVA_USER.name);
  document.querySelectorAll('.avatar-circle').forEach(el => {
    const size = el.classList.contains('sidebar-account-large') || el.style.width === '56px' ? 'large' : 'default';
    el.classList.toggle('has-avatar', Boolean(LEARNOVA_USER.avatarUrl));
    el.innerHTML = getAvatarMarkup(size);
  });
  document.querySelectorAll('.sidebar-email, .sidebar-menu-email').forEach(el => el.textContent = LEARNOVA_USER.email);
  document.querySelectorAll('.sidebar-menu-name').forEach(el => el.textContent = LEARNOVA_USER.name);
  document.querySelectorAll('.tier-badge').forEach(el => {
    el.className = `tier-badge ${isPro ? 'tier-pro' : 'tier-free'}`;
    el.textContent = isPro ? 'Pro' : 'Free';
  });
}

function renderSidebarAccountMenuMarkup() {
  const isPro = LEARNOVA_USER.tier === 'pro';
  return `
    <div class="sidebar-account-card">
      <div class="avatar-circle sidebar-account-large${LEARNOVA_USER.avatarUrl ? ' has-avatar' : ''}">${getAvatarMarkup('large')}</div>
      <div style="min-width:0">
        <div class="sidebar-menu-name">${LEARNOVA_USER.name}</div>
        <div class="sidebar-menu-email">${LEARNOVA_USER.email}</div>
      </div>
      <div class="tier-badge ${isPro?'tier-pro':'tier-free'}" style="margin-top:0;margin-left:auto">${isPro?'Pro':'Free'}</div>
    </div>
    <div class="sidebar-account-actions">
      <button class="sidebar-account-item" type="button" onclick="handleSidebarAccountAction('profile')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="8" cy="5.5" r="2.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5"/></svg>
        <span>Edit profile</span>
      </button>
      <button class="sidebar-account-item" type="button" onclick="handleSidebarAccountAction('accessibility')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="8" cy="8" r="5.5"/><path d="M8 4.5V8l2.2 1.7"/></svg>
        <span>Accessibility settings</span>
      </button>
      <button class="sidebar-account-item" type="button" onclick="handleSidebarAccountAction('plan')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2" y="3" width="12" height="11" rx="2"/><path d="M2 6.5h12M5 1.8v3.1M11 1.8v3.1"/></svg>
        <span>Plan and billing</span>
      </button>
      <div class="sidebar-account-divider"></div>
      <button class="sidebar-account-item sidebar-account-item-signout" type="button" onclick="handleSidebarAccountAction('signout')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M6 3H3.5A1.5 1.5 0 002 4.5v7A1.5 1.5 0 003.5 13H6"/><path d="M9.5 5.5L13 8l-3.5 2.5"/><path d="M5 8h8"/></svg>
        <span>Sign out</span>
      </button>
    </div>
  `;
}

function closeSidebarAccountMenu() {
  const menu = document.getElementById('sidebar-account-mount');
  const trigger = document.getElementById('sidebar-account-trigger');
  const bottom = document.querySelector('.sidebar-bottom');
  if (menu) menu.remove();
  if (trigger) trigger.setAttribute('aria-expanded', 'false');
  if (bottom) bottom.classList.remove('open');
}

function toggleSidebarAccountMenu(event) {
  if (event) event.stopPropagation();
  const existingMenu = document.getElementById('sidebar-account-mount');
  const trigger = document.getElementById('sidebar-account-trigger');
  const bottom = document.querySelector('.sidebar-bottom');
  if (!trigger || !bottom) return;
  if (existingMenu) {
    closeSidebarAccountMenu();
    return;
  }
  const mount = document.createElement('div');
  mount.id = 'sidebar-account-mount';
  mount.innerHTML = `
    <div class="modal-overlay open sidebar-account-overlay" onclick="if(event.target===this)closeSidebarAccountMenu()">
      <div class="modal-box sidebar-account-modal">
        ${renderSidebarAccountMenuMarkup()}
      </div>
    </div>`;
  document.body.appendChild(mount);
  bottom.classList.add('open');
  trigger.setAttribute('aria-expanded', 'true');
}

async function logoutUser() {
  const token = localStorage.getItem('token');
  try {
    if (token) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
    }
  } catch (e) {
    // Network error — continue logout anyway
  } finally {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'index.html';
  }
}

function handleSidebarAccountAction(action) {
  closeSidebarAccountMenu();
  if (action === 'profile') openEditProfile();
  if (action === 'accessibility') openSettings('accessibility');
  if (action === 'plan') window.location.href = 'billing.html';
  if (action === 'signout') logoutUser();
}

/* ── Settings modal ── */
function openSettings(tab='general') {
  const currentTab = tab === 'plan' ? 'plan' : 'accessibility';
  const saved_theme = localStorage.getItem('ln_theme') || 'dark';

  const themeSwatches = [
    { id:'dark',          label:'Dark',           dots:['#0A0A0A','#C8B89A','#6B9E6B'] },
    { id:'light',         label:'Light',          dots:['#F7F5F2','#7A5C38','#2E6E2E'] },
    { id:'high-contrast', label:'High contrast',  dots:['#000000','#FFD700','#00DD00'] },
    { id:'deuteranopia',  label:'Deuteranopia',   dots:['#0A0A0A','#E8B84B','#5B9BD5'] },
    { id:'protanopia',    label:'Protanopia',     dots:['#0A0A0A','#5FB8FF','#FFCC00'] },
    { id:'tritanopia',    label:'Tritanopia',     dots:['#0A0A0A','#FF6E6E','#E8A0D0'] },
  ].map(s => `
    <div class="theme-swatch${saved_theme===s.id?' selected':''}" onclick="applyTheme('${s.id}');document.querySelectorAll('.theme-swatch').forEach(x=>x.classList.remove('selected'));this.classList.add('selected')">
      <div class="swatch-dots">${s.dots.map(c=>`<div class="sd" style="background:${c}"></div>`).join('')}</div>
      <div class="swatch-label">${s.label}</div>
    </div>`).join('');

  const accessibilityPanel = `
    <div style="font-size:12px;color:var(--cream-25);margin-bottom:18px;line-height:1.6">Choose a colour theme that works best for your vision.</div>
    <div class="field-label" style="margin-bottom:10px">Colour theme</div>
    <div class="theme-grid">${themeSwatches}</div>
  `;

  const isPro = LEARNOVA_USER.tier === 'pro';
  const planFeatures = [
    'Unlimited document uploads',
    'PPTX / PowerPoint file support',
    'Upload multiple files at once',
    'Advanced personalised feedback',
    'Full learning modules',
    'Calendar integration',
  ];
  const planPanel = `
    <div class="plan-panel">
      <div class="plan-card plan-current-card">
        <div class="plan-card-head">
          <div class="plan-card-title">Current plan</div>
          <span class="tier-badge ${isPro ? 'tier-pro' : 'tier-free'}">${isPro ? 'Pro' : 'Free'}</span>
        </div>
        <div class="plan-card-copy">
          ${isPro
            ? 'You are on the Pro plan. Premium uploads, advanced feedback, and full learning tools are unlocked for your account.'
            : 'You are on the Free plan. Upgrade to Pro to unlock unlimited documents, PPTX upload, multi-file uploads, and more.'
          }
        </div>
      </div>
      <div class="plan-card plan-upgrade-card">
        <div class="plan-price-title">Learnova Pro — $12/month</div>
        <div class="plan-feature-list">
          ${planFeatures.map(item => `
            <div class="plan-feature-item">
              <span class="plan-feature-dash">—</span>
              <span>${item}</span>
            </div>
          `).join('')}
        </div>
        ${isPro
          ? `<button class="btn btn-primary plan-cta" type="button" onclick="closeSettings();showToast('You are already on Learnova Pro')">Current plan active</button>`
          : `<button class="btn btn-primary plan-cta" type="button" onclick="upgradeToPro()">Upgrade to Pro</button>`
        }
      </div>
    </div>
  `;

  const panel = currentTab === 'plan' ? planPanel : accessibilityPanel;
  const title = currentTab === 'plan' ? 'Plan & billing' : 'Accessibility settings';

  const html = `
  <div class="modal-overlay open" id="settings-overlay" onclick="if(event.target===this)closeSettings()">
    <div class="modal-box">
      <div class="modal-header">
        <div class="modal-title">${title}</div>
        <button class="modal-close" onclick="closeSettings()">✕</button>
      </div>
      <div class="settings-panel active">${panel}</div>
    </div>
  </div>`;

  const el = document.createElement('div');
  el.id = 'settings-mount'; el.innerHTML = html;
  document.body.appendChild(el);
}
function closeSettings() {
  const el = document.getElementById('settings-mount');
  if (el) el.remove();
}

function triggerAvatarUpload() {
  const input = document.getElementById('s-avatar-file');
  if (input) input.click();
}

function handleAvatarUpload(event) {
  const [file] = event.target.files || [];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    showToast('Please upload an image file');
    event.target.value = '';
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const preview = document.getElementById('s-avatar-preview');
    if (!preview) return;
    preview.dataset.avatarUrl = String(reader.result);
    preview.classList.add('has-avatar');
    preview.innerHTML = `<img src="${reader.result}" alt="Avatar preview" class="avatar-image avatar-image-large">`;
  };
  reader.readAsDataURL(file);
}

function openEditProfile() {
  const isPro = LEARNOVA_USER.tier === 'pro';
  const pendingEmailNotice = LEARNOVA_USER.pendingEmail
    ? `<div class="profile-note">Pending email verification for ${escapeHtml(LEARNOVA_USER.pendingEmail)}.</div>`
    : `<div class="profile-note">Email changes stay pending until the new address is verified.</div>`;
  const html = `
  <div class="modal-overlay open" id="edit-profile-overlay" onclick="if(event.target===this)closeEditProfile()">
    <div class="modal-box" style="width:560px;max-width:92vw">
      <div class="modal-header">
        <div class="modal-title">Edit profile</div>
        <button class="modal-close" onclick="closeEditProfile()">✕</button>
      </div>
      <div class="sidebar-account-card" style="margin-bottom:18px">
        <div class="avatar-circle sidebar-account-large${LEARNOVA_USER.avatarUrl ? ' has-avatar' : ''}">${getAvatarMarkup('large')}</div>
        <div style="min-width:0">
          <div class="sidebar-menu-name">${escapeHtml(LEARNOVA_USER.name)}</div>
          <div class="sidebar-menu-email">${escapeHtml(LEARNOVA_USER.email)}</div>
        </div>
        <div class="tier-badge ${isPro ? 'tier-pro' : 'tier-free'}" style="margin-top:0;margin-left:auto">${isPro ? 'Pro' : 'Free'}</div>
      </div>
      <div class="form-field">
        <label class="field-label" for="s-name">Full name</label>
        <input class="input" id="s-name" type="text" value="${escapeHtml(LEARNOVA_USER.name)}" />
      </div>
      <div class="form-field">
        <label class="field-label" for="s-email">Email</label>
        <input class="input" id="s-email" type="email" value="${escapeHtml(LEARNOVA_USER.email)}" />
        ${pendingEmailNotice}
      </div>
      <div class="profile-password-grid">
        <div class="form-field">
          <label class="field-label" for="s-current-password">Current password</label>
          <input class="input" id="s-current-password" type="password" placeholder="Enter current password" />
        </div>
        <div class="form-field">
          <label class="field-label" for="s-new-password">New password</label>
          <input class="input" id="s-new-password" type="password" placeholder="At least 8 characters" />
        </div>
        <div class="form-field">
          <label class="field-label" for="s-confirm-password">Confirm new password</label>
          <input class="input" id="s-confirm-password" type="password" placeholder="Re-enter new password" />
        </div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
        <button class="btn" type="button" onclick="closeEditProfile()">Cancel</button>
        <button class="btn btn-primary" type="button" onclick="saveProfile()">Save changes</button>
      </div>
    </div>
  </div>`;
  const el = document.createElement('div');
  el.id = 'edit-profile-mount';
  el.innerHTML = html;
  document.body.appendChild(el);
}
function closeEditProfile() {
  const el = document.getElementById('edit-profile-mount');
  if (el) el.remove();
}
function saveProfile() {
  const name = document.getElementById('s-name').value.trim();
  const email = document.getElementById('s-email').value.trim();
  const avatarPreview = document.getElementById('s-avatar-preview');
  const currentPassword = document.getElementById('s-current-password').value;
  const newPassword = document.getElementById('s-new-password').value;
  const confirmPassword = document.getElementById('s-confirm-password').value;
  const emailChanged = email && email !== LEARNOVA_USER.email;
  const wantsPasswordChange = Boolean(currentPassword || newPassword || confirmPassword);

  if (name) LEARNOVA_USER.name = name;
  if (avatarPreview) LEARNOVA_USER.avatarUrl = avatarPreview.dataset.avatarUrl || '';
  if (emailChanged) LEARNOVA_USER.pendingEmail = email;
  if (wantsPasswordChange) {
    if (!currentPassword || !newPassword || !confirmPassword) {
      showToast('Fill in all password fields');
      return;
    }
    if (currentPassword !== LEARNOVA_USER.password) {
      showToast('Current password is incorrect');
      return;
    }
    if (newPassword.length < 8) {
      showToast('New password must be at least 8 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast('New passwords do not match');
      return;
    }
    LEARNOVA_USER.password = newPassword;
    LEARNOVA_USER.passwordMask = '•'.repeat(Math.max(7, newPassword.length));
  }
  LEARNOVA_USER.initials = getInitials(LEARNOVA_USER.name);
  closeSettings();
  closeEditProfile();
  if (emailChanged && wantsPasswordChange) showToast('Profile updated. Verify your new email address.');
  else if (emailChanged) showToast('Profile updated. Verify your new email address.');
  else if (wantsPasswordChange) showToast('Password updated');
  else showToast('Profile updated');
  syncUserUI();
}
function upgradeToPro() {
  if (typeof closeSettings === 'function') closeSettings();
  window.location.href = 'billing.html';
}

/* ── Profile modal ── */
function openProfile() {
  const isPro = LEARNOVA_USER.tier === 'pro';
  const html = `
  <div class="modal-overlay open" id="profile-overlay" onclick="if(event.target===this)closeProfile()">
    <div class="modal-box" style="width:580px;max-width:92vw">
      <div class="modal-header">
        <div class="modal-title">Profile</div>
        <button class="modal-close" onclick="closeProfile()">✕</button>
      </div>
      <div style="display:flex;align-items:center;gap:18px;padding:20px;background:var(--cream-05);border:0.5px solid var(--border);border-radius:var(--radius-md);margin-bottom:24px">
        <div class="avatar-circle${LEARNOVA_USER.avatarUrl ? ' has-avatar' : ''}" style="width:56px;height:56px;font-size:18px">${getAvatarMarkup('large')}</div>
        <div style="min-width:0">
          <div style="font-size:20px;font-weight:500;line-height:1.2">${LEARNOVA_USER.name}</div>
          <div style="font-size:14px;color:var(--cream-25);margin-top:4px">${LEARNOVA_USER.email}</div>
          ${LEARNOVA_USER.pendingEmail ? `<div style="font-size:11px;color:var(--gold-dim);margin-top:6px">Pending verification: ${escapeHtml(LEARNOVA_USER.pendingEmail)}</div>` : ''}
          <span class="tier-badge ${isPro?'tier-pro':'tier-free'}" style="margin-top:10px">${isPro?'Pro':'Free'}</span>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr;gap:0.5px;background:var(--border);margin-bottom:20px">
        ${[
          ['Full name', LEARNOVA_USER.name],
          ['Email', LEARNOVA_USER.email],
          ['Date of birth', LEARNOVA_USER.dob],
          ['Phone number', LEARNOVA_USER.phone],
          ['Password', LEARNOVA_USER.passwordMask],
          ['Confirm password', LEARNOVA_USER.passwordMask],
        ].map(([label, value]) => `
          <div style="background:var(--surface);padding:14px 0">
            <div style="font-size:10px;letter-spacing:1.3px;text-transform:uppercase;color:var(--cream-25);margin-bottom:8px">${label}</div>
            <div style="font-size:14px;color:var(--cream-60)">${value}</div>
          </div>
        `).join('')}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <button class="btn" style="justify-content:center" onclick="closeProfile();openEditProfile()">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M2 10.8V12h1.2l6.9-6.9-1.2-1.2L2 10.8z"/><path d="M7.8 3.9l1.2 1.2"/><path d="M9.8 2l1.7 1.7"/></svg>
          Edit
        </button>
        <button class="btn" style="justify-content:center;color:var(--red-soft)" onclick="closeProfile();logoutUser()">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M5 7h7M9 5l2 2-2 2"/><path d="M5 2H2.5a1 1 0 00-1 1v8a1 1 0 001 1H5"/></svg>
          Sign out
        </button>
      </div>
    </div>
  </div>`;
  const el = document.createElement('div'); el.id='profile-mount'; el.innerHTML=html;
  document.body.appendChild(el);
}
function closeProfile() { const el=document.getElementById('profile-mount'); if(el)el.remove(); }

/* ── Sidebar HTML ── */
function renderSidebar(activePage) {
  const isPro = LEARNOVA_USER.tier === 'pro';
  return `
  <aside class="sidebar">
    <div class="sidebar-logo">Learnova</div>
    <div class="sidebar-section">Main</div>
    <a href="dashboard.html" class="sidebar-item${activePage==='dashboard'?' active':''}" data-page="dashboard.html">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/><rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/></svg>
      Dashboard
    </a>
    <a href="upload.html" class="sidebar-item${activePage==='upload'?' active':''}" data-page="upload.html">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M3 2h8l2 2v10H3V2z"/><path d="M9 2v3h3"/><path d="M5 7h6M5 10h4"/></svg>
      Documents
    </a>
    <a href="module.html" class="sidebar-item${activePage==='module'?' active':''}" data-page="module.html">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M2 12V5l6-3 6 3v7"/><path d="M8 2v10"/><path d="M5 10h6"/></svg>
      Learning
    </a>
    <a href="history.html" class="sidebar-item${activePage==='history'?' active':''}" data-page="history.html">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="8" cy="8" r="5.5"/><path d="M8 5v4l2.5 1.5"/></svg>
      History
    </a>
    ${LEARNOVA_USER.role === 'admin' ? `
    <div class="sidebar-section">Admin</div>
    <a href="admin-users.html" class="sidebar-item${activePage==='admin-users'?' active':''}" data-page="admin-users.html">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M11 14v-1a3 3 0 0 0-3-3H5a3 3 0 0 0-3 3v1"/><circle cx="6.5" cy="5.5" r="2.5"/><path d="M14 7h-3M14 10h-3"/></svg>
      Admin Panel
    </a>` : ''}
    <div class="sidebar-section">Account</div>
    <button class="sidebar-item" onclick="openProfile()" style="width:100%;text-align:left;background:none;border:none;color:inherit">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="8" cy="5.5" r="2.5"/><path d="M3 13c0-2.76 2.24-5 5-5s5 2.24 5 5"/></svg>
      Profile
    </button>
    <button class="sidebar-item" onclick="openSettings('accessibility')" style="width:100%;text-align:left;background:none;border:none;color:inherit">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="8" cy="8" r="2"/><path d="M8 2v2M8 12v2M2 8h2M12 8h2"/></svg>
      Settings
    </button>
    <div class="sidebar-bottom">
      <button class="sidebar-avatar sidebar-account-trigger" id="sidebar-account-trigger" type="button" onclick="toggleSidebarAccountMenu(event)" aria-haspopup="true" aria-expanded="false">
        <div class="avatar-circle${LEARNOVA_USER.avatarUrl ? ' has-avatar' : ''}">${getAvatarMarkup('default')}</div>
        <div class="sidebar-avatar-copy">
          <div class="avatar-name">${LEARNOVA_USER.name}</div>
          <div class="sidebar-email">${LEARNOVA_USER.email}</div>
          <div class="tier-badge ${isPro?'tier-pro':'tier-free'}">${isPro?'Pro':'Free'}</div>
        </div>
        <span class="sidebar-avatar-chevron" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M4.5 6.5L8 10l3.5-3.5"/></svg>
        </span>
      </button>
    </div>
  </aside>`;
}

document.addEventListener('DOMContentLoaded', () => {
  loadPrefs();
  const page = location.pathname.split('/').pop() || 'dashboard.html';
  document.querySelectorAll('.sidebar-item[data-page]').forEach(el => {
    if (el.dataset.page === page) el.classList.add('active');
  });

  // Silently revalidate tier from DB on every page load
  const token = localStorage.getItem('token');
  if (token) {
    fetch('/api/auth/profile', { headers: { 'Authorization': 'Bearer ' + token } })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (!data) return;
        const freshTier = data.tier || 'free';
        if (freshTier !== LEARNOVA_USER.tier) {
          LEARNOVA_USER.tier = freshTier;
          const stored = JSON.parse(localStorage.getItem('user') || '{}');
          stored.tier = freshTier;
          localStorage.setItem('user', JSON.stringify(stored));
          syncUserUI();
        }
      })
      .catch(() => {/* network error — keep showing cached value */});
  }
});

document.addEventListener('click', (event) => {
  const bottom = event.target.closest('.sidebar-bottom');
  if (!bottom) closeSidebarAccountMenu();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeSidebarAccountMenu();
});

function ensureHistoryModalMounts() {
  if (!document.getElementById('detail-modal')) {
    const detail = document.createElement('div');
    detail.id = 'detail-modal';
    detail.className = 'detail-modal';
    detail.setAttribute('onclick', 'if(event.target===this)closeHistoryDetail()');
    detail.innerHTML = '<div class="detail-box" id="detail-box"></div>';
    document.body.appendChild(detail);
  }
  if (!document.getElementById('split-modal')) {
    const split = document.createElement('div');
    split.id = 'split-modal';
    split.className = 'detail-modal';
    split.setAttribute('onclick', 'if(event.target===this)closeHistorySplit()');
    split.innerHTML = '<div class="detail-box split-box" id="split-box"></div>';
    document.body.appendChild(split);
  }
}

function openHistoryDetail(id) {
  const item = getHistoryItem(id);
  if (!item || !item.done) return;
  ensureHistoryModalMounts();
  const circ = 251.2;
  const offset = circ - (item.score / 100) * circ;
  document.getElementById('detail-box').innerHTML = `
    <div class="det-header">
      <div class="det-title-row">
        <div class="det-kicker">Quiz complete</div>
        <div class="det-title">Here's how you <em>performed.</em></div>
        <div class="det-doc">${escapeHtml(item.title)} · ${item.total} questions</div>
      </div>
      <div style="text-align:center;flex-shrink:0;margin-left:20px" class="result-step">
        <svg width="90" height="90" viewBox="0 0 110 110">
          <circle cx="55" cy="55" r="40" fill="none" stroke="var(--border)" stroke-width="7"/>
          <circle cx="55" cy="55" r="40" fill="none" stroke="var(--gold)" stroke-width="7" stroke-linecap="round"
            stroke-dasharray="${circ}" stroke-dashoffset="${offset}" transform="rotate(-90 55 55)"/>
          <text x="55" y="55" text-anchor="middle" dominant-baseline="central" font-family="DM Serif Display,serif" font-size="22" fill="currentColor">${item.score}%</text>
        </svg>
        <div style="font-size:11px;color:var(--cream-25);margin-top:4px">${item.correct} of ${item.total} correct</div>
      </div>
      <button class="det-close" onclick="closeHistoryDetail()">✕</button>
    </div>
    <div class="det-panels result-step">
      <div class="det-panel s"><div class="det-ph"><span class="det-dot" style="background:var(--green)"></span><span class="det-pt">Strengths</span></div><div class="tag-cloud">${item.strengths.map(s => `<span class="badge badge-green">${escapeHtml(s)}</span>`).join('')}</div></div>
      <div class="det-panel w"><div class="det-ph"><span class="det-dot" style="background:var(--red-soft)"></span><span class="det-pt">Needs work</span></div><div class="tag-cloud">${item.weaknesses.map(s => `<span class="badge badge-red">${escapeHtml(s)}</span>`).join('')}</div></div>
      <div class="det-panel"><div class="det-ph"><span class="det-dot" style="background:var(--gold)"></span><span class="det-pt">Study next</span></div><div class="tag-cloud">${item.studyNext.map(s => `<span class="badge badge-gold">${escapeHtml(s)}</span>`).join('')}</div></div>
    </div>
    <div class="section-label result-step">Question breakdown</div>
    <div class="q-list result-step">
      ${item.questions.map(q => `
      <div class="q-item ${q.correct ? 'correct' : 'wrong'}">
        <div class="q-row"><span class="q-mark ${q.correct ? 'c' : 'w'}">${q.correct ? '✓' : '✗'}</span><span class="q-text">${escapeHtml(q.q)}</span></div>
        <div class="q-ans">Your answer: ${escapeHtml(q.your)}${!q.correct ? ` &nbsp;·&nbsp; <span class="q-ans-wrong">Correct: ${escapeHtml(q.answer)}</span>` : ''}</div>
      </div>`).join('')}
    </div>
    <div class="det-actions">
      <button class="btn" onclick="closeHistoryDetail()">Back</button>
      <button class="btn" onclick="window.LN.setModalSourceFromEvent(event);closeHistoryDetail();openHistorySplit(${item.id})">Summary + result</button>
      <a href="upload.html" class="btn">Retake quiz</a>
      <a href="module.html" class="btn btn-gold">View learning module →</a>
    </div>
  `;
  document.getElementById('detail-modal').classList.add('open');
  setTimeout(() => {
    const box = document.getElementById('detail-box');
    if (box && window.LN) {
      window.LN.animateModalFromSource(box);
      window.LN.revealSequence(box.querySelectorAll('.result-step'), 90);
    }
    const ring = document.querySelector('#detail-box circle[stroke="var(--gold)"]');
    if (ring && window.LN) window.LN.animateScoreRing(ring, item.score);
  }, 50);
}

function closeHistoryDetail() {
  const modal = document.getElementById('detail-modal');
  if (modal) modal.classList.remove('open');
}

function openHistorySplit(id) {
  const item = getHistoryItem(id);
  if (!item || !item.done) return;
  ensureHistoryModalMounts();
  const circ = 251.2;
  const offset = circ - (item.score / 100) * circ;
  document.getElementById('split-box').innerHTML = `
    <div class="split-header">
      <div>
        <div class="det-kicker">Summary + results</div>
        <div class="det-doc">${escapeHtml(item.title)}</div>
      </div>
      <button class="det-close" onclick="closeHistorySplit()">✕</button>
    </div>
    <div class="split-layout">
      <div class="split-panel split-summary">
        ${renderSummaryMarkup(item, { ctaLabel: 'Retake quiz →', ctaBefore: 'window.LN.setModalSourceFromEvent(event);' })}
      </div>
      <div class="split-panel split-results">
        <div style="text-align:center;margin-bottom:22px" class="result-step">
          <svg width="96" height="96" viewBox="0 0 110 110">
            <circle cx="55" cy="55" r="40" fill="none" stroke="var(--border)" stroke-width="7"/>
            <circle cx="55" cy="55" r="40" fill="none" stroke="var(--gold)" stroke-width="7" stroke-linecap="round"
              stroke-dasharray="${circ}" stroke-dashoffset="${offset}" transform="rotate(-90 55 55)"/>
            <text x="55" y="55" text-anchor="middle" dominant-baseline="central" font-family="DM Serif Display,serif" font-size="22" fill="currentColor">${item.score}%</text>
          </svg>
          <div style="font-size:12px;color:var(--cream-25);margin-top:6px">${item.correct} of ${item.total} correct</div>
        </div>
        <div class="det-panels split-panels result-step">
          <div class="det-panel s"><div class="det-ph"><span class="det-dot" style="background:var(--green)"></span><span class="det-pt">Strengths</span></div><div class="tag-cloud">${item.strengths.map(s => `<span class="badge badge-green">${escapeHtml(s)}</span>`).join('')}</div></div>
          <div class="det-panel w"><div class="det-ph"><span class="det-dot" style="background:var(--red-soft)"></span><span class="det-pt">Needs work</span></div><div class="tag-cloud">${item.weaknesses.map(s => `<span class="badge badge-red">${escapeHtml(s)}</span>`).join('')}</div></div>
          <div class="det-panel"><div class="det-ph"><span class="det-dot" style="background:var(--gold)"></span><span class="det-pt">Study next</span></div><div class="tag-cloud">${item.studyNext.map(s => `<span class="badge badge-gold">${escapeHtml(s)}</span>`).join('')}</div></div>
        </div>
        <div class="section-label result-step">Question breakdown</div>
        <div class="q-list result-step">
          ${item.questions.map(q => `
          <div class="q-item ${q.correct ? 'correct' : 'wrong'}">
            <div class="q-row"><span class="q-mark ${q.correct ? 'c' : 'w'}">${q.correct ? '✓' : '✗'}</span><span class="q-text">${escapeHtml(q.q)}</span></div>
            <div class="q-ans">Your answer: ${escapeHtml(q.your)}${!q.correct ? ` &nbsp;·&nbsp; <span class="q-ans-wrong">Correct: ${escapeHtml(q.answer)}</span>` : ''}</div>
          </div>`).join('')}
        </div>
      </div>
    </div>
  `;
  document.getElementById('split-modal').classList.add('open');
  setTimeout(() => {
    const box = document.getElementById('split-box');
    if (box && window.LN) {
      window.LN.animateModalFromSource(box);
      window.LN.revealSequence(box.querySelectorAll('.result-step'), 90);
    }
    const ring = document.querySelector('#split-box circle[stroke="var(--gold)"]');
    if (ring && window.LN) window.LN.animateScoreRing(ring, item.score);
  }, 50);
}

function closeHistorySplit() {
  const modal = document.getElementById('split-modal');
  if (modal) modal.classList.remove('open');
}

/* ====================================================
   7. SYSTEM ADMIN PAGE
   ==================================================== */

const SYS_SECTIONS = {
  overview: {
    title: 'System Overview',
    sub: 'Monitor service status, realtime stats and API health'
  },
  users: {
    title: 'User Control',
    sub: 'Manage all users across every role'
  },
  database: {
    title: 'Database Manager',
    sub: 'View and manage database collections'
  },
  security: {
    title: 'Security Center',
    sub: 'Monitor activity logs and security events'
  }
};

const SYS_STATE = {
  user: null,
  users: [],
  filteredUsers: [],
  currentSection: 'overview',
  roleTargetUserId: '',
  deleteTargetUserId: '',
  collections: [],
  openCollection: '',
  collectionDocs: {},
  selectedDocs: new Set(),
  dbDeleteTarget: { collection: '', ids: [] },
  logs: [],
  filteredLogs: [],
  securityView: 'activity'
};

function isSystemAdminPage() {
  return Boolean(document.getElementById('system-admin-page'));
}

function renderSystemAdminSidebar(activeSection) {
  const user = SYS_STATE.user || {};
  const name = user.name || 'System Admin';
  const initials = getInitials(name);
  return `
  <aside class="sidebar">
    <div class="sidebar-logo">Learnova</div>
    <div class="sidebar-section">System Admin</div>
    <button class="sidebar-item${activeSection === 'overview' ? ' active' : ''}" id="nav-overview" data-sys-nav="overview" type="button">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
      System Overview
    </button>
    <button class="sidebar-item${activeSection === 'users' ? ' active' : ''}" id="nav-users" data-sys-nav="users" type="button">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      User Control
    </button>
    <button class="sidebar-item${activeSection === 'database' ? ' active' : ''}" id="nav-database" data-sys-nav="database" type="button">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
      Database Manager
    </button>
    <button class="sidebar-item${activeSection === 'security' ? ' active' : ''}" id="nav-security" data-sys-nav="security" type="button">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      Security Center
    </button>
    <div class="sidebar-bottom">
      <button class="sidebar-avatar sidebar-account-trigger" id="sys-sidebar-account-trigger" type="button" aria-haspopup="true" aria-expanded="false">
        <div class="avatar-circle" id="sys-admin-initials">${escapeHtml(initials)}</div>
        <div class="sidebar-avatar-copy">
          <div class="avatar-name" id="sysAdminName">${escapeHtml(name)}</div>
          <div class="sidebar-email">System Admin</div>
        </div>
        <span class="sidebar-avatar-chevron" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M4.5 6.5L8 10l3.5-3.5"/></svg>
        </span>
      </button>
    </div>
  </aside>`;
}

function openSysAccountMenu() {
  const trigger = document.getElementById('sys-sidebar-account-trigger');
  const bottom = document.querySelector('.sidebar-bottom');
  if (!trigger || !bottom) return;
  const existing = document.getElementById('sys-sidebar-account-mount');
  if (existing) {
    closeSysAccountMenu();
    return;
  }
  const user = SYS_STATE.user || {};
  const name = user.name || 'System Admin';
  const email = user.email || '';
  const initials = getInitials(name);

  const mount = document.createElement('div');
  mount.id = 'sys-sidebar-account-mount';
  mount.innerHTML = `
    <div class="modal-overlay open sidebar-account-overlay" id="sys-sidebar-account-overlay">
      <div class="modal-box sidebar-account-modal">
        <div class="sidebar-account-card">
          <div class="avatar-circle sidebar-account-large">${escapeHtml(initials)}</div>
          <div style="min-width:0">
            <div class="sidebar-menu-name">${escapeHtml(name)}</div>
            <div class="sidebar-menu-email">${escapeHtml(email)}</div>
            <div style="font-size:11px;letter-spacing:0.5px;text-transform:uppercase;color:var(--gold);margin-top:6px">System Admin</div>
          </div>
        </div>
        <div class="sidebar-account-actions">
          <button class="sidebar-account-item sidebar-account-item-signout" id="sys-signout-btn" type="button">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M6 3H3.5A1.5 1.5 0 002 4.5v7A1.5 1.5 0 003.5 13H6"/><path d="M9.5 5.5L13 8l-3.5 2.5"/><path d="M5 8h8"/></svg>
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(mount);
  bottom.classList.add('open');
  trigger.setAttribute('aria-expanded', 'true');
}

function closeSysAccountMenu() {
  const mount = document.getElementById('sys-sidebar-account-mount');
  const trigger = document.getElementById('sys-sidebar-account-trigger');
  const bottom = document.querySelector('.sidebar-bottom');
  if (mount) mount.remove();
  if (trigger) trigger.setAttribute('aria-expanded', 'false');
  if (bottom) bottom.classList.remove('open');
}

async function logoutSystemAdmin() {
  closeSysAccountMenu();
  if (typeof logoutUser === 'function') {
    await logoutUser();
    return;
  }
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'index.html';
}

async function verifySysAdmin() {
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = 'index.html';
    return null;
  }
  try {
    const res = await fetch('/api/auth/profile', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) {
      window.location.href = 'index.html';
      return null;
    }
    const user = await res.json();
    if (!user || user.role !== 'system_admin') {
      window.location.href = 'index.html';
      return null;
    }
    return user;
  } catch (_) {
    window.location.href = 'index.html';
    return null;
  }
}

async function sysAdminFetch(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  const res = await fetch(endpoint, {
    ...options,
    headers: {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });

  const rawText = await res.text();
  let data = {};
  try {
    data = rawText ? JSON.parse(rawText) : {};
  } catch (_) {
    data = { message: rawText || '' };
  }

  if (!res.ok) {
    const msg = data.message || data.detail || ('API error: ' + res.status);
    throw new Error(msg);
  }
  return data;
}

async function sysTimedFetch(endpoint, options = {}) {
  const start = performance.now();
  try {
    const data = await sysAdminFetch(endpoint, options);
    return {
      endpoint,
      ok: true,
      ms: Math.round(performance.now() - start),
      data
    };
  } catch (err) {
    return {
      endpoint,
      ok: false,
      ms: Math.round(performance.now() - start),
      data: null,
      error: err.message
    };
  }
}

function switchSysSection(name) {
  if (!SYS_SECTIONS[name]) return;
  SYS_STATE.currentSection = name;

  document.querySelectorAll('.sys-section').forEach(section => section.classList.remove('active'));
  const target = document.getElementById('section-' + name);
  if (target) target.classList.add('active');

  document.querySelectorAll('[data-sys-nav]').forEach(nav => nav.classList.remove('active'));
  const activeNav = document.getElementById('nav-' + name);
  if (activeNav) activeNav.classList.add('active');

  const meta = SYS_SECTIONS[name];
  const pageTitle = document.getElementById('pageTitle');
  const pageSubtitle = document.getElementById('pageSubtitle');
  if (pageTitle) pageTitle.textContent = meta.title;
  if (pageSubtitle) pageSubtitle.textContent = meta.sub;

  if (name === 'overview') loadSystemOverview();
  if (name === 'users') loadUserControl();
  if (name === 'database') {
    loadDatabase();
    scheduleSysDbDetailHeightSync();
  }
  if (name === 'security') {
    SYS_STATE.securityView = 'activity';
    loadSecurity();
    scheduleSysSecurityDetailHeightSync();
  }
}

function showSysLoading(sectionId) {
  const loadingMarkup = '<div class="sys-loading">Loading...</div>';
  if (sectionId === 'section-overview') {
    const statusGrid = document.getElementById('statusGrid');
    const statsGrid = document.getElementById('statsGrid');
    const apiHealthList = document.getElementById('apiHealthList');
    if (statusGrid) statusGrid.innerHTML = loadingMarkup;
    if (statsGrid) statsGrid.innerHTML = loadingMarkup;
    if (apiHealthList) apiHealthList.innerHTML = loadingMarkup;
  }
  if (sectionId === 'section-users') {
    const tbody = document.getElementById('userTableBody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="padding:24px;text-align:center;color:var(--cream-25)">Loading...</td></tr>';
  }
  if (sectionId === 'section-database') {
    const menu = document.getElementById('dbFunctionMenu');
    const detail = document.getElementById('collectionDetail');
    if (menu) menu.innerHTML = loadingMarkup;
    if (detail) detail.innerHTML = '<div class="collection-detail collection-detail-empty"><span class="collection-empty-text">Loading collections...</span></div>';
    scheduleSysDbDetailHeightSync();
  }
  if (sectionId === 'section-security') {
    const menu = document.getElementById('securityFunctionMenu');
    const detail = document.getElementById('securityDetail');
    if (menu) menu.innerHTML = loadingMarkup;
    if (detail) detail.innerHTML = '<div class="collection-detail collection-detail-empty"><span class="collection-empty-text">Loading security data...</span></div>';
    scheduleSysSecurityDetailHeightSync();
  }
}

function renderServiceStatus(healthResult) {
  const statusGrid = document.getElementById('statusGrid');
  if (!statusGrid) return;
  const mongodbState = String((healthResult && healthResult.mongodb) || '').toLowerCase() === 'ok' ? 'online' : 'offline';
  const ollamaState = String((healthResult && healthResult.ollama) || '').toLowerCase() === 'ok' ? 'online' : 'offline';
  const backendState = healthResult ? 'online' : 'offline';

  const services = [
    { name: 'Backend', status: backendState },
    { name: 'AI Model', status: ollamaState },
    { name: 'Database', status: mongodbState }
  ];

  statusGrid.innerHTML = services.map(service => {
    return '<div class="status-item">'
      + '<span class="status-name">' + escapeHtml(service.name) + '</span>'
      + '<span class="status-' + service.status + '">' + (service.status === 'online' ? 'Online' : 'Offline') + '</span>'
      + '</div>';
  }).join('');
}

function renderRealtimeStats(stats) {
  const statsGrid = document.getElementById('statsGrid');
  if (!statsGrid) return;
  const rows = [
    { label: 'Total Users', value: Number(stats.totalUsers || 0).toLocaleString() },
    { label: 'Total Documents', value: Number(stats.totalDocuments || 0).toLocaleString() },
    { label: 'Completed Quizzes', value: Number(stats.totalCompleted || 0).toLocaleString() },
    { label: 'System Logs', value: Number(stats.totalLogs || 0).toLocaleString() }
  ];

  statsGrid.innerHTML = rows.map(row => {
    return '<div class="stat-row">'
      + '<span class="stat-label">' + escapeHtml(row.label) + '</span>'
      + '<span class="stat-val">' + escapeHtml(row.value) + '</span>'
      + '</div>';
  }).join('');
}

function renderApiHealth(requestRows) {
  const apiHealthList = document.getElementById('apiHealthList');
  if (!apiHealthList) return;
  apiHealthList.innerHTML = requestRows.map(row => {
    const icon = row.ok
      ? '<span class="api-ok"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg></span>'
      : '<span class="api-error"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span>';
    return '<div class="api-row">'
      + '<span class="api-endpoint">' + escapeHtml(row.endpoint) + '</span>'
      + '<span class="api-time">' + row.ms + 'ms</span>'
      + icon
      + '</div>';
  }).join('');
}

async function loadSystemOverview() {
  showSysLoading('section-overview');
  const [healthReq, statsReq, logsReq] = await Promise.all([
    sysTimedFetch('/api/sysadmin/health'),
    sysTimedFetch('/api/sysadmin/stats'),
    sysTimedFetch('/api/sysadmin/logs?page=1&limit=20')
  ]);

  if (healthReq.ok) renderServiceStatus(healthReq.data);
  else renderServiceStatus(null);

  if (statsReq.ok) renderRealtimeStats(statsReq.data);
  else {
    const statsGrid = document.getElementById('statsGrid');
    if (statsGrid) statsGrid.innerHTML = '<div class="sys-loading">Failed to load stats</div>';
  }

  renderApiHealth([healthReq, statsReq, logsReq]);

  if (!healthReq.ok || !statsReq.ok || !logsReq.ok) {
    showToast('Failed to load some system overview data', 3200);
  }
}

function formatSysDate(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function normalizeSysUsers(users) {
  return (users || []).map(user => {
    return {
      _id: String(user._id || ''),
      name: user.name || 'Unknown',
      email: user.email || '',
      role: user.role || 'user',
      tier: user.tier || 'free',
      status: user.status || 'active',
      joined: formatSysDate(user.createdAt),
      initials: getInitials(user.name || 'User')
    };
  });
}

function applySysUserFilters() {
  const q = (document.getElementById('sys-user-search')?.value || '').toLowerCase();
  const role = document.getElementById('sys-user-role')?.value || '';
  const status = document.getElementById('sys-user-status')?.value || '';

  SYS_STATE.filteredUsers = SYS_STATE.users.filter(user => {
    const qMatch = !q || user.name.toLowerCase().includes(q) || user.email.toLowerCase().includes(q);
    const roleMatch = !role || user.role === role;
    const statusMatch = !status || user.status === status;
    return qMatch && roleMatch && statusMatch;
  });

  renderUserTable(SYS_STATE.filteredUsers);
}

function renderUserTable(users) {
  const tbody = document.getElementById('userTableBody');
  if (!tbody) return;

  if (!users.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="padding:24px;text-align:center;color:var(--cream-25)">No users found</td></tr>';
    return;
  }

  const roleBadgeMap = {
    system_admin: 'badge-purple',
    admin: 'badge-amber',
    user: 'badge-cream'
  };
  const tierBadgeMap = {
    pro: 'badge-green',
    free: 'badge-cream'
  };

  tbody.innerHTML = users.map(user => {
    const isSelf = SYS_STATE.user && (String(SYS_STATE.user._id) === user._id || SYS_STATE.user.email === user.email);
    return '<tr>'
      + '<td><div class="user-cell"><div class="user-av-sm">' + escapeHtml(user.initials) + '</div><div><div class="user-name-sm">' + escapeHtml(user.name) + '</div><div class="user-email-sm">' + escapeHtml(user.email) + '</div></div></div></td>'
      + '<td><span class="badge ' + (roleBadgeMap[user.role] || 'badge-cream') + '">' + escapeHtml(user.role) + '</span></td>'
      + '<td><span class="badge ' + (tierBadgeMap[user.tier] || 'badge-cream') + '">' + escapeHtml(user.tier) + '</span></td>'
      + '<td><span class="' + (user.status === 'active' ? 'status-dot-green' : 'status-dot-none') + '"></span><span style="font-size:12px;color:var(--cream-60)">' + escapeHtml(user.status) + '</span></td>'
      + '<td style="font-size:12px;color:var(--cream-40)">' + escapeHtml(user.joined) + '</td>'
      + '<td><div class="actions-cell">'
      + '<button class="action-btn sys-role-btn" type="button" data-user-id="' + escapeHtml(user._id) + '" title="Change Role"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="23" y1="11" x2="17" y2="11"/><line x1="20" y1="8" x2="20" y2="14"/></svg></button>'
      + '<button class="action-btn sys-reset-btn" type="button" data-user-id="' + escapeHtml(user._id) + '" title="Reset Password"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></button>'
      + '<button class="action-btn danger sys-delete-btn' + (isSelf ? ' sys-action-disabled' : '') + '" type="button" data-user-id="' + escapeHtml(user._id) + '" title="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/></svg></button>'
      + '</div></td>'
      + '</tr>';
  }).join('');
}

async function loadUserControl() {
  showSysLoading('section-users');
  try {
    const data = await sysAdminFetch('/api/admin/users?page=1&limit=100');
    SYS_STATE.users = normalizeSysUsers(data.users || []);
    applySysUserFilters();
  } catch (err) {
    const tbody = document.getElementById('userTableBody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="padding:24px;text-align:center;color:var(--red-soft)">Failed to load users</td></tr>';
    showToast('Failed to load users', 3200);
  }
}

function openSysRoleModal(userId) {
  const user = SYS_STATE.users.find(item => item._id === userId);
  if (!user) return;
  SYS_STATE.roleTargetUserId = user._id;
  const targetName = document.getElementById('sysRoleTargetName');
  const roleSelect = document.getElementById('sysRoleSelect');
  if (targetName) targetName.textContent = user.name;
  if (roleSelect) roleSelect.value = user.role;
  document.getElementById('sysRoleOverlay')?.classList.add('open');
}

function closeSysRoleModal() {
  SYS_STATE.roleTargetUserId = '';
  document.getElementById('sysRoleOverlay')?.classList.remove('open');
}

async function changeSysUserRole(userId, newRole) {
  const confirmBtn = document.getElementById('sysRoleConfirmBtn');
  if (confirmBtn) confirmBtn.disabled = true;
  try {
    await sysAdminFetch('/api/admin/users/' + encodeURIComponent(userId) + '/role', {
      method: 'PUT',
      body: JSON.stringify({ role: newRole })
    });
    closeSysRoleModal();
    showToast('Role updated', 2800);
    await loadUserControl();
  } catch (_) {
    showToast('Failed to update role', 3200);
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
  }
}

async function resetSysUserPassword(userId) {
  try {
    await sysAdminFetch('/api/admin/user/' + encodeURIComponent(userId) + '/reset-password', {
      method: 'POST'
    });
    showToast('Password reset to Learnova@2026', 3000);
  } catch (_) {
    showToast('Failed to reset password', 3200);
  }
}

function openSysDeleteModal(userId) {
  const user = SYS_STATE.users.find(item => item._id === userId);
  if (!user) return;
  SYS_STATE.deleteTargetUserId = user._id;
  const targetName = document.getElementById('sysDeleteTargetName');
  const input = document.getElementById('sysDeleteInput');
  const confirmBtn = document.getElementById('sysDeleteConfirmBtn');
  if (targetName) targetName.textContent = user.name;
  if (input) input.value = '';
  if (confirmBtn) confirmBtn.disabled = true;
  document.getElementById('sysDeleteOverlay')?.classList.add('open');
}

function closeSysDeleteModal() {
  SYS_STATE.deleteTargetUserId = '';
  document.getElementById('sysDeleteOverlay')?.classList.remove('open');
}

function syncSysDeleteConfirmButton() {
  const user = SYS_STATE.users.find(item => item._id === SYS_STATE.deleteTargetUserId);
  const input = document.getElementById('sysDeleteInput');
  const confirmBtn = document.getElementById('sysDeleteConfirmBtn');
  if (!user || !input || !confirmBtn) return;
  confirmBtn.disabled = input.value !== user.name;
}

async function deleteSysUser(userId) {
  const confirmBtn = document.getElementById('sysDeleteConfirmBtn');
  if (confirmBtn) confirmBtn.disabled = true;
  try {
    await sysAdminFetch('/api/admin/users/' + encodeURIComponent(userId), {
      method: 'DELETE'
    });
    closeSysDeleteModal();
    showToast('User deleted', 2800);
    await loadUserControl();
  } catch (_) {
    showToast('Failed to delete user', 3200);
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
  }
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return size.toFixed(size >= 100 || idx === 0 ? 0 : 1) + ' ' + units[idx];
}

function estimateCollectionSize(items, totalCount) {
  if (!items || !items.length || !totalCount) return '0 B';
  const sampleBytes = JSON.stringify(items).length / items.length;
  return formatBytes(Math.round(sampleBytes * totalCount));
}

function syncSysDbDetailHeight() {
  if (SYS_STATE.currentSection !== 'database') return;
  const detailContainer = document.getElementById('collectionDetail');
  if (!detailContainer) return;

  const rect = detailContainer.getBoundingClientRect();
  const bottomGap = window.innerWidth <= 760 ? 16 : 24;
  const contentShell = detailContainer.closest('.content');
  const shellBottomPadding = contentShell ? (parseFloat(window.getComputedStyle(contentShell).paddingBottom) || 0) : 0;
  const availableHeight = Math.max(260, Math.floor(window.innerHeight - rect.top - bottomGap - shellBottomPadding));

  detailContainer.style.height = availableHeight + 'px';
  detailContainer.style.minHeight = availableHeight + 'px';
  detailContainer.style.maxHeight = availableHeight + 'px';

  const detailCard = detailContainer.querySelector('.collection-detail');
  let cardTargetHeight = availableHeight;
  if (detailCard) {
    const cardStyle = window.getComputedStyle(detailCard);
    const cardOuterGap = (parseFloat(cardStyle.marginTop) || 0) + (parseFloat(cardStyle.marginBottom) || 0);
    cardTargetHeight = Math.max(140, availableHeight - cardOuterGap);
    detailCard.style.minHeight = cardTargetHeight + 'px';
  }

  const docList = detailContainer.querySelector('#sys-doc-list');
  if (docList) {
    const header = detailContainer.querySelector('.collection-detail-header');
    const footer = detailContainer.querySelector('.collection-detail-footer');
    const occupiedHeight = (header ? header.offsetHeight : 0) + (footer ? footer.offsetHeight : 0);
    docList.style.maxHeight = Math.max(120, cardTargetHeight - occupiedHeight - 2) + 'px';
  }
}

function scheduleSysDbDetailHeightSync() {
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(syncSysDbDetailHeight);
    return;
  }
  setTimeout(syncSysDbDetailHeight, 0);
}

function syncSysSecurityDetailHeight() {
  if (SYS_STATE.currentSection !== 'security') return;
  const detailContainer = document.getElementById('securityDetail');
  if (!detailContainer) return;

  const rect = detailContainer.getBoundingClientRect();
  const bottomGap = window.innerWidth <= 760 ? 16 : 24;
  const contentShell = detailContainer.closest('.content');
  const shellBottomPadding = contentShell ? (parseFloat(window.getComputedStyle(contentShell).paddingBottom) || 0) : 0;
  const availableHeight = Math.max(260, Math.floor(window.innerHeight - rect.top - bottomGap - shellBottomPadding));

  detailContainer.style.height = availableHeight + 'px';
  detailContainer.style.minHeight = availableHeight + 'px';
  detailContainer.style.maxHeight = availableHeight + 'px';

  const detailCard = detailContainer.querySelector('.collection-detail');
  let cardTargetHeight = availableHeight;
  if (detailCard) {
    const cardStyle = window.getComputedStyle(detailCard);
    const cardOuterGap = (parseFloat(cardStyle.marginTop) || 0) + (parseFloat(cardStyle.marginBottom) || 0);
    cardTargetHeight = Math.max(140, availableHeight - cardOuterGap);
    detailCard.style.minHeight = cardTargetHeight + 'px';
  }

  const scrollArea = detailContainer.querySelector('.security-detail-scroll');
  if (scrollArea) {
    const header = detailContainer.querySelector('.collection-detail-header');
    const occupiedHeight = header ? header.offsetHeight : 0;
    scrollArea.style.maxHeight = Math.max(120, cardTargetHeight - occupiedHeight - 2) + 'px';
  }
}

function scheduleSysSecurityDetailHeightSync() {
  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(syncSysSecurityDetailHeight);
    return;
  }
  setTimeout(syncSysSecurityDetailHeight, 0);
}

function getCollectionDetailEmptyMarkup(message) {
  return '<div class="collection-detail collection-detail-empty"><span class="collection-empty-text">' + escapeHtml(message) + '</span></div>';
}

async function fetchSysCollectionNames() {
  const probe = await sysAdminFetch('/api/sysadmin/db/__collections__?page=1&limit=1');
  if (!probe || !probe.error) return [];
  const match = String(probe.error).match(/Allowed:\s*\[(.*)\]/);
  if (!match || !match[1]) return [];
  try {
    const listJson = ('[' + match[1] + ']').replace(/'/g, '"');
    const parsed = JSON.parse(listJson);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

async function loadDatabase() {
  showSysLoading('section-database');
  try {
    const names = await fetchSysCollectionNames();
    if (!names.length) {
      const menu = document.getElementById('dbFunctionMenu');
      const detail = document.getElementById('collectionDetail');
      if (menu) menu.innerHTML = '<div class="sys-loading">No collections available</div>';
      if (detail) detail.innerHTML = getCollectionDetailEmptyMarkup('No data to display.');
      scheduleSysDbDetailHeightSync();
      return;
    }

    const rows = await Promise.all(names.map(async name => {
      try {
        const data = await sysAdminFetch('/api/sysadmin/db/' + encodeURIComponent(name) + '?page=1&limit=5');
        const total = Number(data.total || 0);
        return {
          name,
          total,
          size: estimateCollectionSize(data.items || [], total),
          preview: data.items || []
        };
      } catch (_) {
        return {
          name,
          total: 0,
          size: '0 B',
          preview: []
        };
      }
    }));

    SYS_STATE.collections = rows;
    SYS_STATE.collectionDocs = {};
    SYS_STATE.openCollection = '';
    renderCollections(rows);
    scheduleSysDbDetailHeightSync();
  } catch (_) {
    const menu = document.getElementById('dbFunctionMenu');
    const detail = document.getElementById('collectionDetail');
    if (menu) menu.innerHTML = '<div class="sys-loading" style="color:var(--red-soft)">Failed to load collections</div>';
    if (detail) detail.innerHTML = getCollectionDetailEmptyMarkup('Unable to display data right now.');
    showToast('Failed to load database', 3200);
    scheduleSysDbDetailHeightSync();
  }
}

function renderCollections(collections) {
  const menu = document.getElementById('dbFunctionMenu');
  if (!menu) return;
  if (!collections.length) {
    menu.innerHTML = '<div class="sys-loading">No collections found</div>';
    return;
  }

  menu.innerHTML = collections.map(item => {
    const isOpen = SYS_STATE.openCollection === item.name;
    return '<button class="db-func-btn' + (isOpen ? ' active' : '') + '" type="button" data-expand-collection="' + escapeHtml(item.name) + '">'
      + '<span class="db-func-name">' + escapeHtml(item.name) + '</span>'
      + '<span class="db-func-meta">' + Number(item.total || 0).toLocaleString() + ' docs - ' + escapeHtml(item.size) + '</span>'
      + '</button>';
  }).join('');

  const detail = document.getElementById('collectionDetail');
  if (detail && !SYS_STATE.openCollection) {
    detail.innerHTML = getCollectionDetailEmptyMarkup('Select a collection from the menu above to view data.');
  }
  scheduleSysDbDetailHeightSync();
}

async function expandCollection(name) {
  const detail = document.getElementById('collectionDetail');
  if (!detail) return;

  if (SYS_STATE.openCollection === name) {
    SYS_STATE.openCollection = '';
    renderCollections(SYS_STATE.collections);
    return;
  }

  SYS_STATE.openCollection = name;
  renderCollections(SYS_STATE.collections);
  detail.innerHTML = '<div class="sys-loading">Loading collection...</div>';
  scheduleSysDbDetailHeightSync();

  try {
    const data = await sysAdminFetch('/api/sysadmin/db/' + encodeURIComponent(name) + '?page=1&limit=20');
    SYS_STATE.collectionDocs[name] = data.items || [];
    renderCollectionDocs(name, SYS_STATE.collectionDocs[name]);
  } catch (_) {
    detail.innerHTML = '<div class="sys-loading">Failed to load collection data</div>';
    showToast('Failed to load collection', 3200);
  }
}

function renderCollectionDocs(name, docs) {
  const detail = document.getElementById('collectionDetail');
  if (!detail) return;

  SYS_STATE.selectedDocs = new Set();

  const rows = docs.map(item => {
    const id = escapeHtml(String(item._id || ''));
    const json = escapeHtml(JSON.stringify(item, null, 2));
    return '<div class="doc-row" data-doc-id="' + id + '" data-doc-json="' + escapeHtml(JSON.stringify(item)) + '">'
      + '<input class="doc-checkbox" type="checkbox" data-doc-id="' + id + '">'
      + '<span class="doc-content">' + json + '</span>'
      + '</div>';
  }).join('');

  const loadedCount = docs.length;
  detail.innerHTML = '<div class="collection-detail">'
    + '<div class="collection-detail-header">'
    + '<span class="collection-detail-title">' + escapeHtml(name) + ' — ' + loadedCount + ' documents loaded</span>'
    + '<div style="display:flex;gap:8px;align-items:center">'
    + '<label class="doc-select-all-wrap"><input type="checkbox" id="sys-select-all"> Select all</label>'
    + '<button class="btn btn-outline btn-sm" type="button" id="sys-collapse-collection">Collapse</button>'
    + '</div>'
    + '</div>'
    + '<div class="doc-list" id="sys-doc-list">' + (rows || '<div class="doc-row"><span class="doc-content">No documents</span></div>') + '</div>'
    + '<div class="collection-detail-footer">'
    + '<input class="detail-search" id="sys-detail-search" type="text" placeholder="Search by content...">'
    + '<div class="sys-collection-actions">'
    + '<button class="btn btn-outline btn-sm" type="button" id="sys-delete-selected" disabled>Delete Selected (<span id="sys-delete-count">0</span>)</button>'
    + '<button class="btn btn-danger btn-sm" type="button" id="sys-clear-all">Clear All (' + loadedCount + ')</button>'
    + '</div>'
    + '</div>'
    + '</div>';

  scheduleSysDbDetailHeightSync();
}

function updateDeleteSelectedBtn() {
  const btn = document.getElementById('sys-delete-selected');
  const countEl = document.getElementById('sys-delete-count');
  if (!btn) return;
  const count = SYS_STATE.selectedDocs.size;
  btn.disabled = count === 0;
  if (countEl) countEl.textContent = String(count);
}

function openSysDbDeleteModal(collection, ids, mode) {
  SYS_STATE.dbDeleteTarget = { collection, ids };
  const title = document.getElementById('sysDbDeleteTitle');
  const msg = document.getElementById('sysDbDeleteMsg');
  if (title) title.textContent = mode === 'all' ? 'Clear All Documents' : 'Delete Selected Documents';
  if (msg) {
    if (mode === 'all') {
      msg.innerHTML = 'This will permanently delete all <strong>' + ids.length + '</strong> loaded documents from <strong>' + escapeHtml(collection) + '</strong>. This cannot be undone.';
    } else {
      msg.innerHTML = 'Delete <strong>' + ids.length + '</strong> selected document' + (ids.length !== 1 ? 's' : '') + ' from <strong>' + escapeHtml(collection) + '</strong>? This cannot be undone.';
    }
  }
  document.getElementById('sysDbDeleteOverlay')?.classList.add('open');
}

function closeSysDbDeleteModal() {
  SYS_STATE.dbDeleteTarget = { collection: '', ids: [] };
  document.getElementById('sysDbDeleteOverlay')?.classList.remove('open');
}

async function deleteSelectedDocs() {
  const { collection, ids } = SYS_STATE.dbDeleteTarget;
  if (!collection || !ids.length) return;
  const confirmBtn = document.getElementById('sysDbDeleteConfirmBtn');
  if (confirmBtn) confirmBtn.disabled = true;
  try {
    const result = await sysAdminFetch('/api/sysadmin/db/' + encodeURIComponent(collection) + '/documents', {
      method: 'DELETE',
      body: JSON.stringify({ ids })
    });
    closeSysDbDeleteModal();
    showToast('Deleted ' + (result.deleted || ids.length) + ' document' + (ids.length !== 1 ? 's' : ''), 2800);
    SYS_STATE.selectedDocs = new Set();
    await expandCollection(collection);
  } catch (err) {
    showToast(err.message || 'Failed to delete', 3200);
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
  }
}

function filterCollectionDocs(query) {
  const list = document.getElementById('sys-doc-list');
  if (!list) return;
  const q = String(query || '').toLowerCase();
  list.querySelectorAll('.doc-row').forEach(row => {
    const source = (row.getAttribute('data-doc-json') || '').toLowerCase();
    row.style.display = !q || source.includes(q) ? '' : 'none';
  });
}

function classifyLogType(log) {
  const path = String(log.path || '').toLowerCase();
  const status = Number(log.status || 0);
  if (path.includes('/auth/login') && status >= 400) return 'failed';
  if (path.includes('/auth/login')) return 'login';
  if (path.includes('/upload')) return 'upload';
  if (path.includes('/quiz') || path.includes('/results') || path.includes('/modules') || path.includes('submit-quiz')) return 'quiz';
  if (path.includes('/admin') || path.includes('/sysadmin')) return 'admin';
  if (status >= 500) return 'error';
  return 'error';
}

function formatTimeAgo(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.max(1, Math.floor(diffMs / 60000));
  if (diffMin < 60) return diffMin + ' min ago';
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return diffHr + ' hr ago';
  const diffDay = Math.floor(diffHr / 24);
  return diffDay + ' day ago';
}

function renderFailedLogins(logs) {
  const failedList = document.getElementById('failedLoginList');
  if (!failedList) return;

  const failed = logs.filter(log => classifyLogType(log) === 'failed');
  const grouped = {};
  failed.forEach(log => {
    const key = log.ip || 'unknown';
    if (!grouped[key]) grouped[key] = { ip: key, attempts: 0, latest: log.timestamp };
    grouped[key].attempts += 1;
    if (new Date(log.timestamp) > new Date(grouped[key].latest)) grouped[key].latest = log.timestamp;
  });

  const rows = Object.values(grouped).sort((a, b) => b.attempts - a.attempts);
  if (!rows.length) {
    failedList.innerHTML = '<div class="failed-row-item"><span class="f-email">No failed logins found</span></div>';
    return;
  }

  failedList.innerHTML = rows.map(row => {
    const highRisk = row.attempts >= 5;
    return '<div class="failed-row-item">'
      + '<span class="f-email">' + escapeHtml(row.ip) + '</span>'
      + '<span class="f-count">x ' + row.attempts + ' attempts</span>'
      + '<span class="badge ' + (highRisk ? 'badge-red' : 'badge-amber') + '">' + (highRisk ? 'High' : 'Medium') + '</span>'
      + '<span class="f-time">' + escapeHtml(formatTimeAgo(row.latest)) + '</span>'
      + '</div>';
  }).join('');
}

function filterActivityLogs(type) {
  if (!SYS_STATE.logs.length) return [];
  if (!type || type === 'all') return SYS_STATE.logs.slice();
  return SYS_STATE.logs.filter(log => classifyLogType(log) === type);
}

function renderActivityLogs(logs) {
  const activityList = document.getElementById('activityLogList');
  if (!activityList) return;
  const type = document.getElementById('sys-log-filter')?.value || 'all';
  const filtered = filterActivityLogs(type);
  SYS_STATE.filteredLogs = filtered;

  if (!filtered.length) {
    activityList.innerHTML = '<div class="log-row-item"><span class="event-desc">No events for this filter</span></div>';
    return;
  }

  const header = '<div class="log-col-header">'
    + '<span class="lch-type">Type</span>'
    + '<span class="lch-ip">IP Address</span>'
    + '<span class="lch-user">Username</span>'
    + '<span class="lch-api">Endpoint</span>'
    + '<span class="lch-time">Time</span>'
    + '</div>';

  const rows = filtered.map(log => {
    const eventType = classifyLogType(log);
    const labelMap = {
      login: 'LOGIN',
      upload: 'UPLOAD',
      quiz: 'QUIZ',
      failed: 'FAIL',
      admin: 'ADMIN',
      error: 'ERROR'
    };
    const method = escapeHtml(log.method || 'GET');
    const path = escapeHtml(log.path || '-');
    const status = escapeHtml(String(log.status || '-'));
    const username = log.user_email ? escapeHtml(log.user_email) : '<span class="event-anon">guest</span>';
    return '<div class="log-row-item">'
      + '<span class="log-col lc-type"><span class="event-indicator ei-' + eventType + '"></span><span class="event-label">' + labelMap[eventType] + '</span></span>'
      + '<span class="log-col lc-ip">' + escapeHtml(log.ip || '-') + '</span>'
      + '<span class="log-col lc-user">' + username + '</span>'
      + '<span class="log-col lc-api"><span class="lc-method">' + method + '</span> ' + path + ' <span class="lc-status">' + status + '</span></span>'
      + '<span class="log-col lc-time">' + escapeHtml(formatTimeAgo(log.timestamp)) + '</span>'
      + '</div>';
  }).join('');

  activityList.innerHTML = header + rows;
}

function renderAuditTrail(logs) {
  const auditList = document.getElementById('auditTrailList');
  if (!auditList) return;

  const rows = logs
    .filter(log => {
      const path = String(log.path || '').toLowerCase();
      const method = String(log.method || '').toUpperCase();
      return (path.includes('/api/admin') || path.includes('/api/sysadmin')) && method !== 'GET';
    })
    .slice(0, 50);

  if (!rows.length) {
    auditList.innerHTML = '<div class="audit-row-item"><div class="audit-text"><div class="audit-line"><span class="audit-subject">No admin actions found</span></div></div></div>';
    return;
  }

  const iconByMethod = {
    POST: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
    PUT: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>',
    DELETE: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/></svg>'
  };

  auditList.innerHTML = rows.map(log => {
    const method = String(log.method || '').toUpperCase();
    const path = String(log.path || '');
    const status = String(log.status || '-');
    const icon = iconByMethod[method] || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18"/></svg>';
    return '<div class="audit-row-item">'
      + '<div class="audit-icon-sm">' + icon + '</div>'
      + '<div class="audit-text">'
      + '<div class="audit-line">'
      + '<span class="audit-actor">System Admin</span>'
      + '<span class="audit-arrow">-></span>'
      + '<span class="audit-verb">' + escapeHtml(method) + '</span>'
      + '<span class="audit-arrow">-></span>'
      + '<span class="audit-subject">' + escapeHtml(path.replace('/api/', '')) + '</span>'
      + '<span class="audit-change-tag">Status ' + escapeHtml(status) + '</span>'
      + '</div>'
      + '<div class="audit-time-sm">' + escapeHtml(formatTimeAgo(log.timestamp)) + '</div>'
      + '</div>'
      + '</div>';
  }).join('');
}

function getSecurityViewsMeta() {
  const failedCount = SYS_STATE.logs.filter(log => classifyLogType(log) === 'failed').length;
  const auditCount = SYS_STATE.logs.filter(log => {
    const path = String(log.path || '').toLowerCase();
    const method = String(log.method || '').toUpperCase();
    return (path.includes('/api/admin') || path.includes('/api/sysadmin')) && method !== 'GET';
  }).length;

  return {
    failed: failedCount,
    activity: SYS_STATE.logs.length,
    audit: auditCount
  };
}

function renderSecurityFunctionMenu() {
  const menu = document.getElementById('securityFunctionMenu');
  if (!menu) return;
  const items = [
    { key: 'activity', label: 'Activity Logs' },
    { key: 'audit', label: 'Audit Trail' },
    { key: 'failed', label: 'Failed Logins' }
  ];

  menu.innerHTML = items.map(item => {
    const active = SYS_STATE.securityView === item.key;
    return '<button class="db-func-btn' + (active ? ' active' : '') + '" type="button" data-security-view="' + item.key + '">'
      + '<span class="db-func-name">' + item.label + '</span>'
      + '</button>';
  }).join('');
}

function renderSecurityDetail() {
  const detail = document.getElementById('securityDetail');
  if (!detail) return;

  if (SYS_STATE.securityView === 'activity') {
    detail.innerHTML = '<div class="collection-detail">'
      + '<div class="collection-detail-header">'
      + '<span class="collection-detail-title">Activity Logs</span>'
      + '<div class="sys-card-actions">'
      + '<select class="filter-select" id="sys-log-filter">'
      + '<option value="all">All Events</option>'
      + '<option value="login">Login</option>'
      + '<option value="upload">Upload</option>'
      + '<option value="quiz">Quiz</option>'
      + '<option value="failed">Failed Login</option>'
      + '<option value="admin">Admin</option>'
      + '<option value="error">Error</option>'
      + '</select>'
      + '<button class="btn btn-outline btn-sm" id="sys-export-logs" type="button">'
      + '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
      + 'Export'
      + '</button>'
      + '</div>'
      + '</div>'
      + '<div class="security-detail-scroll" id="activityLogList"></div>'
      + '</div>';
    renderActivityLogs(SYS_STATE.logs);
    scheduleSysSecurityDetailHeightSync();
    return;
  }

  if (SYS_STATE.securityView === 'audit') {
    detail.innerHTML = '<div class="collection-detail">'
      + '<div class="collection-detail-header">'
      + '<span class="collection-detail-title">Audit Trail - Admin Actions</span>'
      + '</div>'
      + '<div class="security-detail-scroll" id="auditTrailList"></div>'
      + '</div>';
    renderAuditTrail(SYS_STATE.logs);
    scheduleSysSecurityDetailHeightSync();
    return;
  }

  detail.innerHTML = '<div class="collection-detail">'
    + '<div class="collection-detail-header">'
    + '<span class="collection-detail-title">Failed Logins</span>'
    + '</div>'
    + '<div class="security-detail-scroll" id="failedLoginList"></div>'
    + '</div>';
  renderFailedLogins(SYS_STATE.logs);
  scheduleSysSecurityDetailHeightSync();
}

function openSecurityView(view) {
  const next = String(view || '').toLowerCase();
  if (!['failed', 'activity', 'audit'].includes(next)) return;
  SYS_STATE.securityView = next;
  renderSecurityFunctionMenu();
  renderSecurityDetail();
}

async function loadSecurity() {
  showSysLoading('section-security');
  try {
    const data = await sysAdminFetch('/api/sysadmin/logs?page=1&limit=1000');
    SYS_STATE.logs = (data.logs || []).slice();
    if (!['failed', 'activity', 'audit'].includes(SYS_STATE.securityView)) {
      SYS_STATE.securityView = 'activity';
    }
    renderSecurityFunctionMenu();
    renderSecurityDetail();
  } catch (_) {
    showToast('Failed to load security data', 3200);
    const menu = document.getElementById('securityFunctionMenu');
    const detail = document.getElementById('securityDetail');
    if (menu) menu.innerHTML = '<div class="sys-loading" style="color:var(--red-soft)">Failed to load security functions</div>';
    if (detail) detail.innerHTML = getCollectionDetailEmptyMarkup('Unable to display security data right now.');
    scheduleSysSecurityDetailHeightSync();
  }
}

function exportSysLogsCsv() {
  const rows = SYS_STATE.filteredLogs.length ? SYS_STATE.filteredLogs : SYS_STATE.logs;
  if (!rows.length) {
    showToast('No logs to export', 2800);
    return;
  }

  const header = ['method', 'path', 'status', 'ip', 'timestamp'];
  const lines = [header.join(',')].concat(rows.map(log => {
    return [
      log.method || '',
      log.path || '',
      log.status || '',
      log.ip || '',
      log.timestamp || ''
    ].map(value => '"' + String(value).replace(/"/g, '""') + '"').join(',');
  }));

  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'system-logs.csv';
  a.click();
  URL.revokeObjectURL(url);
  showToast('CSV exported', 2800);
}

function bindSystemAdminEvents() {
  window.addEventListener('resize', () => {
    scheduleSysDbDetailHeightSync();
    scheduleSysSecurityDetailHeightSync();
  });

  const mount = document.getElementById('sidebar-mount');
  if (mount) {
    mount.addEventListener('click', event => {
      const nav = event.target.closest('[data-sys-nav]');
      if (nav) {
        switchSysSection(nav.getAttribute('data-sys-nav'));
        return;
      }
      const trigger = event.target.closest('#sys-sidebar-account-trigger');
      if (trigger) {
        event.stopPropagation();
        openSysAccountMenu();
      }
    });
  }

  document.addEventListener('click', event => {
    const overlay = event.target.closest('#sys-sidebar-account-overlay');
    if (overlay && event.target === overlay) {
      closeSysAccountMenu();
      return;
    }
    const signout = event.target.closest('#sys-signout-btn');
    if (signout) {
      logoutSystemAdmin();
      return;
    }
    if (!event.target.closest('.sidebar-bottom') && !event.target.closest('#sys-sidebar-account-mount')) {
      closeSysAccountMenu();
    }
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeSysAccountMenu();
      closeSysRoleModal();
      closeSysDeleteModal();
      closeSysDbDeleteModal();
    }
  });

  document.getElementById('sys-refresh-overview')?.addEventListener('click', () => {
    loadSystemOverview();
  });

  document.getElementById('sys-user-search')?.addEventListener('input', applySysUserFilters);
  document.getElementById('sys-user-role')?.addEventListener('change', applySysUserFilters);
  document.getElementById('sys-user-status')?.addEventListener('change', applySysUserFilters);

  document.getElementById('userTableBody')?.addEventListener('click', event => {
    const roleBtn = event.target.closest('.sys-role-btn');
    if (roleBtn) {
      openSysRoleModal(roleBtn.getAttribute('data-user-id') || '');
      return;
    }
    const resetBtn = event.target.closest('.sys-reset-btn');
    if (resetBtn) {
      resetSysUserPassword(resetBtn.getAttribute('data-user-id') || '');
      return;
    }
    const deleteBtn = event.target.closest('.sys-delete-btn:not(.sys-action-disabled)');
    if (deleteBtn) {
      openSysDeleteModal(deleteBtn.getAttribute('data-user-id') || '');
    }
  });

  document.getElementById('sysRoleCancelBtn')?.addEventListener('click', closeSysRoleModal);
  document.getElementById('sysRoleConfirmBtn')?.addEventListener('click', () => {
    const userId = SYS_STATE.roleTargetUserId;
    const role = document.getElementById('sysRoleSelect')?.value;
    if (!userId || !role) return;
    changeSysUserRole(userId, role);
  });

  document.getElementById('sysRoleOverlay')?.addEventListener('click', event => {
    if (event.target.id === 'sysRoleOverlay') closeSysRoleModal();
  });

  document.getElementById('sysDeleteCancelBtn')?.addEventListener('click', closeSysDeleteModal);
  document.getElementById('sysDeleteInput')?.addEventListener('input', syncSysDeleteConfirmButton);
  document.getElementById('sysDeleteConfirmBtn')?.addEventListener('click', () => {
    if (!SYS_STATE.deleteTargetUserId) return;
    deleteSysUser(SYS_STATE.deleteTargetUserId);
  });

  document.getElementById('sysDeleteOverlay')?.addEventListener('click', event => {
    if (event.target.id === 'sysDeleteOverlay') closeSysDeleteModal();
  });

  document.getElementById('sysDbDeleteCancelBtn')?.addEventListener('click', closeSysDbDeleteModal);
  document.getElementById('sysDbDeleteConfirmBtn')?.addEventListener('click', deleteSelectedDocs);
  document.getElementById('sysDbDeleteOverlay')?.addEventListener('click', event => {
    if (event.target.id === 'sysDbDeleteOverlay') closeSysDbDeleteModal();
  });

  document.getElementById('dbFunctionMenu')?.addEventListener('click', event => {
    const btn = event.target.closest('[data-expand-collection]');
    if (!btn) return;
    const name = btn.getAttribute('data-expand-collection') || '';
    if (!name) return;
    expandCollection(name);
  });

  document.getElementById('collectionDetail')?.addEventListener('input', event => {
    if (event.target && event.target.id === 'sys-detail-search') {
      filterCollectionDocs(event.target.value || '');
    }
  });

  document.getElementById('collectionDetail')?.addEventListener('change', event => {
    const selectAll = event.target.closest('#sys-select-all');
    if (selectAll) {
      const checked = selectAll.checked;
      document.querySelectorAll('.doc-checkbox').forEach(cb => {
        cb.checked = checked;
        const id = cb.getAttribute('data-doc-id') || '';
        if (!id) return;
        if (checked) {
          SYS_STATE.selectedDocs.add(id);
        } else {
          SYS_STATE.selectedDocs.delete(id);
        }
        cb.closest('.doc-row')?.classList.toggle('doc-row-selected', checked);
      });
      updateDeleteSelectedBtn();
      return;
    }
    const checkbox = event.target.closest('.doc-checkbox');
    if (checkbox) {
      const id = checkbox.getAttribute('data-doc-id') || '';
      if (!id) return;
      if (checkbox.checked) {
        SYS_STATE.selectedDocs.add(id);
      } else {
        SYS_STATE.selectedDocs.delete(id);
        const selectAllEl = document.getElementById('sys-select-all');
        if (selectAllEl) selectAllEl.checked = false;
      }
      checkbox.closest('.doc-row')?.classList.toggle('doc-row-selected', checkbox.checked);
      updateDeleteSelectedBtn();
    }
  });

  document.getElementById('collectionDetail')?.addEventListener('click', event => {
    const collapse = event.target.closest('#sys-collapse-collection');
    if (collapse) {
      if (SYS_STATE.openCollection) expandCollection(SYS_STATE.openCollection);
      return;
    }
    const deleteSelBtn = event.target.closest('#sys-delete-selected:not([disabled])');
    if (deleteSelBtn) {
      const ids = Array.from(SYS_STATE.selectedDocs);
      if (!ids.length) return;
      openSysDbDeleteModal(SYS_STATE.openCollection, ids, 'selected');
      return;
    }
    const clearAllBtn = event.target.closest('#sys-clear-all');
    if (clearAllBtn) {
      const allDocs = SYS_STATE.collectionDocs[SYS_STATE.openCollection] || [];
      const allIds = allDocs.map(d => String(d._id || '')).filter(Boolean);
      if (!allIds.length) { showToast('No documents loaded', 2800); return; }
      openSysDbDeleteModal(SYS_STATE.openCollection, allIds, 'all');
    }
  });

  document.getElementById('securityFunctionMenu')?.addEventListener('click', event => {
    const btn = event.target.closest('[data-security-view]');
    if (!btn) return;
    openSecurityView(btn.getAttribute('data-security-view') || 'failed');
  });

  document.getElementById('securityDetail')?.addEventListener('change', event => {
    if (event.target && event.target.id === 'sys-log-filter') {
      renderActivityLogs(SYS_STATE.logs);
      scheduleSysSecurityDetailHeightSync();
    }
  });

  document.getElementById('securityDetail')?.addEventListener('click', event => {
    const exportBtn = event.target.closest('#sys-export-logs');
    if (exportBtn) exportSysLogsCsv();
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  if (!isSystemAdminPage()) return;

  const user = await verifySysAdmin();
  if (!user) return;

  SYS_STATE.user = user;

  const sidebarMount = document.getElementById('sidebar-mount');
  if (sidebarMount) {
    sidebarMount.innerHTML = renderSystemAdminSidebar('overview');
  }

  const nameSlot = document.getElementById('sysAdminName');
  const initialsSlot = document.getElementById('sys-admin-initials');
  if (nameSlot) nameSlot.textContent = user.name || 'System Admin';
  if (initialsSlot) initialsSlot.textContent = getInitials(user.name || 'System Admin');

  bindSystemAdminEvents();
  switchSysSection('overview');
});
