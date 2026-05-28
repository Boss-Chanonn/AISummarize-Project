/* Shared JWT session expiry handling for authenticated pages. */
(function () {
  const TOKEN_KEY = 'token';
  const USER_KEY = 'user';
  const MESSAGE_KEY = 'learnova_session_message';
  const PUBLIC_PAGES = new Set(['', 'index.html', 'register.html']);
  const AUTH_EXCLUDED_PATHS = new Set([
    '/api/auth/login',
    '/api/auth/register'
  ]);

  let expiryTimer = null;

  function getCurrentPage() {
    return window.location.pathname.split('/').pop() || '';
  }

  function isPublicPage() {
    return PUBLIC_PAGES.has(getCurrentPage());
  }

  function decodeJwtPayload(token) {
    if (!token || token.split('.').length < 2) return null;
    try {
      const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), '=');
      return JSON.parse(window.atob(padded));
    } catch (error) {
      return null;
    }
  }

  function clearTimer() {
    if (expiryTimer) {
      window.clearTimeout(expiryTimer);
      expiryTimer = null;
    }
  }

  function logoutExpiredSession(message) {
    clearTimer();
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.setItem(
      MESSAGE_KEY,
      message || 'Your session has expired. Please sign in again.'
    );

    if (!isPublicPage()) {
      window.location.replace('index.html');
    }
  }

  function scheduleSessionExpiry() {
    clearTimer();

    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;

    const payload = decodeJwtPayload(token);
    if (!payload || !payload.exp) return;

    const expiresAtMs = Number(payload.exp) * 1000;
    const delayMs = expiresAtMs - Date.now();

    if (delayMs <= 0) {
      logoutExpiredSession();
      return;
    }

    expiryTimer = window.setTimeout(logoutExpiredSession, delayMs);
  }

  function getApiPath(resource) {
    try {
      const rawUrl = typeof resource === 'string' ? resource : resource && resource.url;
      if (!rawUrl) return '';
      return new URL(rawUrl, window.location.origin).pathname;
    } catch (error) {
      return '';
    }
  }

  function shouldLogoutForResponse(resource, response) {
    if (!localStorage.getItem(TOKEN_KEY)) return false;
    if (!response || response.status !== 401) return false;

    const path = getApiPath(resource);
    if (!path.startsWith('/api/')) return false;
    return !AUTH_EXCLUDED_PATHS.has(path);
  }

  const originalFetch = window.fetch;
  if (typeof originalFetch === 'function' && !window.__learnovaSessionFetchWrapped) {
    window.__learnovaSessionFetchWrapped = true;
    window.fetch = function (resource, options) {
      return originalFetch.apply(this, arguments).then(function (response) {
        if (shouldLogoutForResponse(resource, response)) {
          logoutExpiredSession('Your session is no longer valid. Please sign in again.');
        }
        return response;
      });
    };
  }

  window.learnovaSession = {
    schedule: scheduleSessionExpiry,
    logoutExpired: logoutExpiredSession
  };

  window.addEventListener('storage', function (event) {
    if (event.key === TOKEN_KEY) scheduleSessionExpiry();
  });

  scheduleSessionExpiry();
})();
