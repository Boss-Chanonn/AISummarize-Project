/* -- Logout handler — overrides app.js signout to call real backend -- */

function handleSidebarAccountAction(action) {
  closeSidebarAccountMenu();
  if (action === 'profile') openEditProfile();
  if (action === 'accessibility') openSettings('accessibility');
  if (action === 'plan') openSettings('plan');
  if (action === 'signout') logoutUser();
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
    window.location.href = 'landing.html';
  }
}
