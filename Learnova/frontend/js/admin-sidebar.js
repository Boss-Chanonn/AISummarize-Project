/* ── Admin Sidebar — shared component for all admin pages ── */

/* ── JWT Guard + globals ─────────────────────────────────────────────────────── */
var TOKEN   = localStorage.getItem('token');
var _stored = JSON.parse(localStorage.getItem('user') || 'null');

if (!TOKEN || !_stored || !['admin', 'system_admin'].includes(_stored.role)) {
  window.location.href = 'index.html';
}

var AUTH = { Authorization: 'Bearer ' + TOKEN };

/* ── Nav definition ──────────────────────────────────────────────────────────── */
var _ADMIN_NAV = [
  {
    section: 'Overview',
    items: [
      {
        label: 'Dashboard',
        href:  'dashboard.html',
        badge: false,
        icon:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>'
      }
    ]
  },
  {
    section: 'Admin',
    items: [
      {
        label: 'User Management',
        href:  'admin-users.html',
        badge: true,
        icon:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
      },
      {
        label: 'Stats Overview',
        href:  'admin-stats.html',
        badge: true,
        icon:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>'
      },
      {
        label: 'History',
        href:  'admin-history.html',
        badge: false,
        icon:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/></svg>'
      }
    ]
  }
];

if (_stored && _stored.role === 'admin') {
  _ADMIN_NAV = _ADMIN_NAV.map(function(group) {
    if (group.section !== 'Overview') return group;
    return {
      section: group.section,
      items: group.items.filter(function(item) { return item.href !== 'dashboard.html'; })
    };
  }).filter(function(group) {
    return group.items && group.items.length > 0;
  });
}

/* ── Logout ──────────────────────────────────────────────────────────────────── */
function logoutAdmin() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'index.html';
}

/* ── Admin account popup ─────────────────────────────────────────────────────── */
function _adminCloseAccountMenu() {
  var menu = document.getElementById('admin-account-mount');
  var trigger = document.getElementById('admin-account-trigger');
  var bottom = document.querySelector('.sidebar-bottom');
  if (menu) menu.remove();
  if (trigger) trigger.setAttribute('aria-expanded', 'false');
  if (bottom) bottom.classList.remove('open');
}

function _adminEscapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function _adminGetInitials(name) {
  return String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(function (part) { return part[0].toUpperCase(); })
    .join('') || 'A';
}

function _adminGetAvatarMarkup(size) {
  var safeSize = size || 'large';
  if (!_stored || !_stored.avatarUrl) return _adminEscapeHtml(_adminGetInitials((_stored && _stored.name) || 'Admin'));
  return '<img src="' + _adminEscapeHtml(_stored.avatarUrl) + '" alt="' + _adminEscapeHtml((_stored && _stored.name) || 'Admin') + '" class="avatar-image avatar-image-' + safeSize + '">';
}

function _adminShowToast(msg) {
  if (typeof showToast === 'function') {
    showToast(msg, 'success');
    return;
  }
  var toast = document.getElementById('toast');
  var toastMsg = document.getElementById('toastMsg');
  if (toast && toastMsg) {
    toastMsg.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function() { toast.classList.remove('show'); }, 2800);
  }
}

function _adminToggleAccountMenu(event) {
  if (event) event.stopPropagation();
  var existing = document.getElementById('admin-account-mount');
  var trigger = document.getElementById('admin-account-trigger');
  var bottom = document.querySelector('.sidebar-bottom');
  if (!trigger || !bottom) return;
  if (existing) { _adminCloseAccountMenu(); return; }

  var name  = (_stored && _stored.name)  || 'Admin';
  var email = (_stored && _stored.email) || '';
  var isPro = (_stored && _stored.tier) === 'pro';
  var tierLabel = isPro ? 'Pro' : 'Free';
  var initials = name.split(' ').map(function(w){ return w[0]; }).join('').toUpperCase().slice(0,2) || '?';

  var mount = document.createElement('div');
  mount.id = 'admin-account-mount';
  mount.innerHTML = '<div class="modal-overlay open sidebar-account-overlay" onclick="if(event.target===this)_adminCloseAccountMenu()">'
    + '<div class="modal-box sidebar-account-modal">'
    +   '<div class="sidebar-account-card">'
    +     '<div class="avatar-circle sidebar-account-large" style="background:rgba(200,184,154,0.15);color:var(--gold);font-size:16px;font-weight:500">' + initials + '</div>'
    +     '<div style="min-width:0">'
    +       '<div class="sidebar-menu-name">' + _adminEscapeHtml(name) + '</div>'
    +       '<div class="sidebar-menu-email">' + _adminEscapeHtml(email) + '</div>'
    +     '</div>'
    +     '<div class="tier-badge ' + (isPro ? 'tier-pro' : 'tier-free') + '" style="margin-top:0;margin-left:auto">' + tierLabel + '</div>'
    +   '</div>'
    +   '<div class="sidebar-account-actions">'
    +     '<button class="sidebar-account-item" type="button" onclick="_adminCloseAccountMenu();_adminOpenEditProfile()">'
    +       '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M11.5 2.5a1.4 1.4 0 012 2L7 11l-2.5.5L5 9l6.5-6.5z"/><path d="M2.5 13.5h11"/></svg>'
    +       '<span>Edit profile</span>'
    +     '</button>'
    +     '<button class="sidebar-account-item" type="button" onclick="_adminCloseAccountMenu();_adminOpenAccessibility()">'
    +       '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="8" cy="8" r="5.5"/><path d="M8 4.5V8l2.2 1.7"/></svg>'
    +       '<span>Accessibility settings</span>'
    +     '</button>'
    +     '<div class="sidebar-account-divider"></div>'
    +     '<button class="sidebar-account-item sidebar-account-item-signout" type="button" onclick="logoutAdmin()">'
    +       '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M6 3H3.5A1.5 1.5 0 002 4.5v7A1.5 1.5 0 003.5 13H6"/><path d="M9.5 5.5L13 8l-3.5 2.5"/><path d="M5 8h8"/></svg>'
    +       '<span>Sign out</span>'
    +     '</button>'
    +   '</div>'
    + '</div>'
    + '</div>';
  document.body.appendChild(mount);
  bottom.classList.add('open');
  trigger.setAttribute('aria-expanded', 'true');
}

function _adminOpenEditProfile() {
  var isPro = (_stored && _stored.tier) === 'pro';
  var currentName = (_stored && _stored.name) || '';
  var currentEmail = (_stored && _stored.email) || '';
  var pendingEmail = (_stored && _stored.pendingEmail) || '';
  var pendingEmailNotice = pendingEmail
    ? '<div class="profile-note">Pending email verification for ' + _adminEscapeHtml(pendingEmail) + '.</div>'
    : '<div class="profile-note">Email changes stay pending until the new address is verified.</div>';

  var html = '<div class="modal-overlay open" id="admin-edit-profile-overlay" onclick="if(event.target===this)_adminCloseEditProfile()">'
    + '<div class="modal-box" style="width:560px;max-width:92vw">'
    +   '<div class="modal-header">'
    +     '<div class="modal-title">Edit profile</div>'
    +     '<button class="modal-close" onclick="_adminCloseEditProfile()">✕</button>'
    +   '</div>'
    +   '<div class="sidebar-account-card" style="margin-bottom:18px">'
    +     '<div class="avatar-circle sidebar-account-large' + ((_stored && _stored.avatarUrl) ? ' has-avatar' : '') + '">' + _adminGetAvatarMarkup('large') + '</div>'
    +     '<div style="min-width:0">'
    +       '<div class="sidebar-menu-name">' + _adminEscapeHtml(currentName || 'Admin') + '</div>'
    +       '<div class="sidebar-menu-email">' + _adminEscapeHtml(currentEmail || '') + '</div>'
    +     '</div>'
    +     '<div class="tier-badge ' + (isPro ? 'tier-pro' : 'tier-free') + '" style="margin-top:0;margin-left:auto">' + (isPro ? 'Pro' : 'Free') + '</div>'
    +   '</div>'
    +   '<div class="form-field">'
    +     '<label class="field-label" for="admin-edit-name">Full name</label>'
    +     '<input class="input" id="admin-edit-name" type="text" value="' + _adminEscapeHtml(currentName) + '">'
    +   '</div>'
    +   '<div class="form-field">'
    +     '<label class="field-label" for="admin-edit-email">Email</label>'
    +     '<input class="input" id="admin-edit-email" type="email" value="' + _adminEscapeHtml(currentEmail) + '">'
    +     pendingEmailNotice
    +   '</div>'
    +   '<div class="profile-password-grid">'
    +     '<div class="form-field">'
    +       '<label class="field-label" for="admin-current-password">Current password</label>'
    +       '<input class="input" id="admin-current-password" type="password" placeholder="Enter current password">'
    +     '</div>'
    +     '<div class="form-field">'
    +       '<label class="field-label" for="admin-new-password">New password</label>'
    +       '<input class="input" id="admin-new-password" type="password" placeholder="At least 8 characters">'
    +     '</div>'
    +     '<div class="form-field">'
    +       '<label class="field-label" for="admin-confirm-password">Confirm new password</label>'
    +       '<input class="input" id="admin-confirm-password" type="password" placeholder="Re-enter new password">'
    +     '</div>'
    +   '</div>'
    +   '<div id="admin-edit-error" style="display:none;color:var(--red-soft);font-size:12px;margin:6px 0 14px"></div>'
    +   '<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">'
    +     '<button class="btn" type="button" onclick="_adminCloseEditProfile()">Cancel</button>'
    +     '<button class="btn btn-primary" id="admin-edit-save" type="button" onclick="_adminSaveProfile()">Save changes</button>'
    +   '</div>'
    + '</div>'
    + '</div>';

  var el = document.createElement('div');
  el.id = 'admin-edit-profile-mount';
  el.innerHTML = html;
  document.body.appendChild(el);
}

function _adminCloseEditProfile() {
  var el = document.getElementById('admin-edit-profile-mount');
  if (el) el.remove();
}

async function _adminSaveProfile() {
  var nameInput = document.getElementById('admin-edit-name');
  var emailInput = document.getElementById('admin-edit-email');
  var currentPasswordInput = document.getElementById('admin-current-password');
  var newPasswordInput = document.getElementById('admin-new-password');
  var confirmPasswordInput = document.getElementById('admin-confirm-password');
  var errorEl = document.getElementById('admin-edit-error');
  var saveBtn = document.getElementById('admin-edit-save');
  if (!nameInput || !emailInput || !currentPasswordInput || !newPasswordInput || !confirmPasswordInput || !errorEl || !saveBtn) return;

  var name = (nameInput.value || '').trim();
  var email = (emailInput.value || '').trim();
  var currentPassword = currentPasswordInput.value || '';
  var newPassword = newPasswordInput.value || '';
  var confirmPassword = confirmPasswordInput.value || '';
  var emailChanged = Boolean(email && _stored && email !== _stored.email);
  var wantsPasswordChange = Boolean(currentPassword || newPassword || confirmPassword);

  if (!name || !email) {
    errorEl.textContent = 'Please fill in both name and email.';
    errorEl.style.display = 'block';
    return;
  }

  if (wantsPasswordChange) {
    if (!currentPassword || !newPassword || !confirmPassword) {
      errorEl.textContent = 'Fill in all password fields';
      errorEl.style.display = 'block';
      return;
    }
    if (newPassword.length < 8) {
      errorEl.textContent = 'New password must be at least 8 characters';
      errorEl.style.display = 'block';
      return;
    }
    if (newPassword !== confirmPassword) {
      errorEl.textContent = 'New passwords do not match';
      errorEl.style.display = 'block';
      return;
    }
  }

  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';
  errorEl.style.display = 'none';

  try {
    if (wantsPasswordChange) {
      var passRes = await fetch('/api/auth/password', {
        method: 'PUT',
        headers: { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      });
      var passData = {};
      try { passData = await passRes.json(); } catch (_) {}
      if (!passRes.ok) {
        errorEl.textContent = passData.message || 'Unable to update password.';
        errorEl.style.display = 'block';
        return;
      }
    }

    var profileRes = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, email: email })
    });
    var profileData = {};
    try { profileData = await profileRes.json(); } catch (_) {}
    if (!profileRes.ok) {
      errorEl.textContent = profileData.message || 'Unable to update profile.';
      errorEl.style.display = 'block';
      return;
    }

    if (_stored) {
      _stored.name = name;
      _stored.email = email;
      _stored.pendingEmail = emailChanged ? email : '';
      localStorage.setItem('user', JSON.stringify(_stored));
    }

    var initials = _adminGetInitials(name);
    var nameEl = document.getElementById('adminName');
    var initialsEl = document.getElementById('adminInitials');
    if (nameEl) nameEl.textContent = name;
    if (initialsEl) initialsEl.textContent = initials;

    _adminCloseEditProfile();
    if (emailChanged && wantsPasswordChange) _adminShowToast('Profile updated. Verify your new email address.');
    else if (emailChanged) _adminShowToast('Profile updated. Verify your new email address.');
    else if (wantsPasswordChange) _adminShowToast('Password updated');
    else _adminShowToast('Profile updated');
  } catch (e) {
    errorEl.textContent = 'Network error. Please try again.';
    errorEl.style.display = 'block';
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save changes';
  }
}

function _adminOpenAccessibility() {
  var saved_theme = localStorage.getItem('ln_theme') || 'dark';
  var THEMES = ['dark','light','high-contrast','deuteranopia','protanopia','tritanopia'];
  var LABELS = { dark:'Dark', light:'Light', 'high-contrast':'High contrast', deuteranopia:'Deuteranopia', protanopia:'Protanopia', tritanopia:'Tritanopia' };
  var DOTS   = { dark:['#0A0A0A','#C8B89A','#6B9E6B'], light:['#F7F5F2','#7A5C38','#2E6E2E'], 'high-contrast':['#000000','#FFD700','#00DD00'], deuteranopia:['#0A0A0A','#E8B84B','#5B9BD5'], protanopia:['#0A0A0A','#5FB8FF','#FFCC00'], tritanopia:['#0A0A0A','#FF6E6E','#E8A0D0'] };

  var swatches = THEMES.map(function(id) {
    var dots = DOTS[id].map(function(c){ return '<div style="width:12px;height:12px;border-radius:50%;background:' + c + '"></div>'; }).join('');
    return '<div class="theme-swatch' + (saved_theme === id ? ' selected' : '') + '" onclick="(function(id,el){' +
      'if(id===\'dark\')document.documentElement.removeAttribute(\'data-theme\');' +
      'else document.documentElement.setAttribute(\'data-theme\',id);' +
      'localStorage.setItem(\'ln_theme\',id);' +
      'document.querySelectorAll(\'.theme-swatch\').forEach(function(x){x.classList.remove(\'selected\')});' +
      'el.classList.add(\'selected\');' +
      '})(\''+id+'\',this)">'
      + '<div class="swatch-dots">' + dots + '</div>'
      + '<div class="swatch-label">' + LABELS[id] + '</div>'
      + '</div>';
  }).join('');

  var html = '<div class="modal-overlay open" id="admin-accessibility-overlay" onclick="if(event.target===this)_adminCloseAccessibility()">'
    + '<div class="modal-box">'
    +   '<div class="modal-header">'
    +     '<div class="modal-title">Accessibility settings</div>'
    +     '<button class="modal-close" onclick="_adminCloseAccessibility()">✕</button>'
    +   '</div>'
    +   '<div style="font-size:12px;color:var(--cream-25);margin-bottom:18px;line-height:1.6">Choose a colour theme that works best for your vision.</div>'
    +   '<div class="field-label" style="margin-bottom:10px">Colour theme</div>'
    +   '<div class="theme-grid">' + swatches + '</div>'
    + '</div>'
    + '</div>';

  var el = document.createElement('div');
  el.id = 'admin-accessibility-mount';
  el.innerHTML = html;
  document.body.appendChild(el);
}

function _adminCloseAccessibility() {
  var el = document.getElementById('admin-accessibility-mount');
  if (el) el.remove();
}

document.addEventListener('click', function(event) {
  if (!event.target.closest('.sidebar-bottom')) _adminCloseAccountMenu();
});
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') { _adminCloseAccountMenu(); _adminCloseAccessibility(); _adminCloseEditProfile(); }
});

/* ── Inject sidebar on DOM ready ─────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  var sidebar = document.getElementById('adminSidebar');
  if (!sidebar) return;

  var currentPage = location.pathname.split('/').pop() || 'index.html';

  var html = '<div class="sidebar-logo">Learn<span>ova</span></div>';

  _ADMIN_NAV.forEach(function (group) {
    html += '<div class="sidebar-section">' + group.section + '</div>';

    group.items.forEach(function (item) {
      var isActive = item.href === currentPage;

      if (item.onclick) {
        /* action item (e.g. Sign Out) */
        html += '<div class="sidebar-item" onclick="' + item.onclick + '">'
              + item.icon + ' ' + item.label
              + '</div>';
      } else {
        /* link item */
        html += '<a href="' + item.href + '" class="sidebar-item' + (isActive ? ' active' : '') + '">'
              + item.icon + ' ' + item.label;
        html += '</a>';
      }
    });
  });

  html += '<div class="sidebar-bottom">'
        +   '<button class="sidebar-avatar sidebar-account-trigger" id="admin-account-trigger" type="button" onclick="_adminToggleAccountMenu(event)" aria-haspopup="true" aria-expanded="false">'
        +     '<div class="avatar-circle" id="adminInitials" style="background:rgba(200,184,154,0.15);color:var(--gold);font-size:12px;font-weight:500">\u2014</div>'
        +     '<div class="sidebar-avatar-copy">'
        +       '<div class="avatar-name" id="adminName">Loading\u2026</div>'
        +       '<div class="sidebar-email" id="adminRole">Admin</div>'
        +     '</div>'
        +     '<span class="sidebar-avatar-chevron" aria-hidden="true">'
        +       '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M4.5 6.5L8 10l3.5-3.5"/></svg>'
        +     '</span>'
        +   '</button>'
        + '</div>';

  sidebar.innerHTML = html;

  /* Populate admin identity */
  if (_stored) {
    var initials = (_stored.name || '').split(' ').map(function (w) { return w[0]; }).join('').toUpperCase().slice(0, 2);
    document.getElementById('adminInitials').textContent = initials || '?';
    document.getElementById('adminName').textContent     = _stored.name || 'Admin';
    document.getElementById('adminRole').textContent     = _stored.role === 'system_admin' ? 'System Admin' : 'Admin';
  }
});
