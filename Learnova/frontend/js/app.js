/* â”€â”€ Learnova shared JS â”€â”€ */

/* â”€â”€ User state (loaded from localStorage after login) â”€â”€ */
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
  passwordMask: 'â€¢â€¢â€¢â€¢â€¢â€¢â€¢',
  tier: (_storedUser && _storedUser.tier) || 'free',
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
  const ctaLabel = options.ctaLabel || (item.done ? 'Retake quiz â†’' : 'Continue to quiz â†’');
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
      ${item.summary.takeaways.map(point => `<div class="kp-item"><span class="kp-dash">â€”</span>${escapeHtml(point)}</div>`).join('')}
    </div>
    <div class="quiz-cta">
      <div class="cta-hint">${ctaHint}</div>
      <button class="btn btn-primary" onclick="${ctaBefore}${ctaHandler}">${ctaLabel}</button>
    </div>
  `;
}

/* â”€â”€ Theme / accessibility engine â”€â”€ */
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

/* â”€â”€ Toast â”€â”€ */
function showToast(msg, duration=2800) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div'); t.id='toast'; t.className='toast';
    t.innerHTML='<div class="toast-dot"></div><span id="toast-msg"></span>';
    document.body.appendChild(t);
  }
  document.getElementById('toast-msg').textContent = msg;
  t.classList.add('show'); clearTimeout(t._timer);
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
        <div class="tier-badge ${isPro?'tier-pro':'tier-free'}">${isPro?'Pro':'Free'}</div>
      </div>
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

/* â”€â”€ Settings modal â”€â”€ */
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
        <div class="plan-price-title">Learnova Pro â€” $12/month</div>
        <div class="plan-feature-list">
          ${planFeatures.map(item => `
            <div class="plan-feature-item">
              <span class="plan-feature-dash">â€”</span>
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
        <button class="modal-close" onclick="closeSettings()">âœ•</button>
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
  const pendingEmailNotice = LEARNOVA_USER.pendingEmail
    ? `<div class="profile-note">Pending email verification for ${escapeHtml(LEARNOVA_USER.pendingEmail)}.</div>`
    : `<div class="profile-note">Email changes stay pending until the new address is verified.</div>`;
  const html = `
  <div class="modal-overlay open" id="edit-profile-overlay" onclick="if(event.target===this)closeEditProfile()">
    <div class="modal-box" style="width:560px;max-width:92vw">
      <div class="modal-header">
        <div class="modal-title">Edit profile</div>
        <button class="modal-close" onclick="closeEditProfile()">âœ•</button>
      </div>
      <div class="profile-avatar-editor">
        <div class="avatar-circle profile-avatar-preview${LEARNOVA_USER.avatarUrl ? ' has-avatar' : ''}" id="s-avatar-preview" data-avatar-url="${escapeHtml(LEARNOVA_USER.avatarUrl)}">${getAvatarMarkup('large')}</div>
        <div style="flex:1">
          <div class="field-label">Profile photo / avatar</div>
          <div class="profile-note" style="margin-bottom:12px">Upload a square image for the cleanest result.</div>
          <input id="s-avatar-file" type="file" accept="image/*" style="display:none" onchange="handleAvatarUpload(event)">
          <button class="btn" type="button" onclick="triggerAvatarUpload()">Upload photo</button>
        </div>
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
    LEARNOVA_USER.passwordMask = 'â€¢'.repeat(Math.max(7, newPassword.length));
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

/* â”€â”€ Profile modal â”€â”€ */
function openProfile() {
  const isPro = LEARNOVA_USER.tier === 'pro';
  const html = `
  <div class="modal-overlay open" id="profile-overlay" onclick="if(event.target===this)closeProfile()">
    <div class="modal-box" style="width:580px;max-width:92vw">
      <div class="modal-header">
        <div class="modal-title">Profile</div>
        <button class="modal-close" onclick="closeProfile()">âœ•</button>
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

/* â”€â”€ Sidebar HTML â”€â”€ */
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
        <div class="det-doc">${escapeHtml(item.title)} Â· ${item.total} questions</div>
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
      <button class="det-close" onclick="closeHistoryDetail()">âœ•</button>
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
        <div class="q-row"><span class="q-mark ${q.correct ? 'c' : 'w'}">${q.correct ? 'âœ“' : 'âœ—'}</span><span class="q-text">${escapeHtml(q.q)}</span></div>
        <div class="q-ans">Your answer: ${escapeHtml(q.your)}${!q.correct ? ` &nbsp;Â·&nbsp; <span class="q-ans-wrong">Correct: ${escapeHtml(q.answer)}</span>` : ''}</div>
      </div>`).join('')}
    </div>
    <div class="det-actions">
      <button class="btn" onclick="closeHistoryDetail()">Back</button>
      <button class="btn" onclick="window.LN.setModalSourceFromEvent(event);closeHistoryDetail();openHistorySplit(${item.id})">Summary + result</button>
      <a href="upload.html" class="btn">Retake quiz</a>
      <a href="module.html" class="btn btn-gold">View learning module â†’</a>
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
      <button class="det-close" onclick="closeHistorySplit()">âœ•</button>
    </div>
    <div class="split-layout">
      <div class="split-panel split-summary">
        ${renderSummaryMarkup(item, { ctaLabel: 'Retake quiz â†’', ctaBefore: 'window.LN.setModalSourceFromEvent(event);' })}
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
            <div class="q-row"><span class="q-mark ${q.correct ? 'c' : 'w'}">${q.correct ? 'âœ“' : 'âœ—'}</span><span class="q-text">${escapeHtml(q.q)}</span></div>
            <div class="q-ans">Your answer: ${escapeHtml(q.your)}${!q.correct ? ` &nbsp;Â·&nbsp; <span class="q-ans-wrong">Correct: ${escapeHtml(q.answer)}</span>` : ''}</div>
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
