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
      }
    ]
  }
];

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

function _adminToggleAccountMenu(event) {
  if (event) event.stopPropagation();
  var existing = document.getElementById('admin-account-mount');
  var trigger = document.getElementById('admin-account-trigger');
  var bottom = document.querySelector('.sidebar-bottom');
  if (!trigger || !bottom) return;
  if (existing) { _adminCloseAccountMenu(); return; }

  var name  = (_stored && _stored.name)  || 'Admin';
  var email = (_stored && _stored.email) || '';
  var role  = (_stored && _stored.role === 'system_admin') ? 'System Admin' : 'Admin';
  var initials = name.split(' ').map(function(w){ return w[0]; }).join('').toUpperCase().slice(0,2) || '?';

  var mount = document.createElement('div');
  mount.id = 'admin-account-mount';
  mount.innerHTML = '<div class="modal-overlay open sidebar-account-overlay" onclick="if(event.target===this)_adminCloseAccountMenu()">'
    + '<div class="modal-box sidebar-account-modal">'
    +   '<div class="sidebar-account-card">'
    +     '<div class="avatar-circle sidebar-account-large" style="background:rgba(200,184,154,0.15);color:var(--gold);font-size:16px;font-weight:500">' + initials + '</div>'
    +     '<div style="min-width:0">'
    +       '<div class="sidebar-menu-name">' + name + '</div>'
    +       '<div class="sidebar-menu-email">' + email + '</div>'
    +       '<div style="font-size:11px;letter-spacing:0.5px;text-transform:uppercase;color:var(--gold);margin-top:6px">' + role + '</div>'
    +     '</div>'
    +   '</div>'
    +   '<div class="sidebar-account-actions">'
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
  if (event.key === 'Escape') { _adminCloseAccountMenu(); _adminCloseAccessibility(); }
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
