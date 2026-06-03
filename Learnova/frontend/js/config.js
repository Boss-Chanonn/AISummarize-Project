/**
 * ── Learnova Config ──
 *
 * Global configuration object used across all frontend pages.
 * Defines default values for API endpoints, user state, upload limits,
 * dashboard metadata, learning module defaults, and an empty history array.
 *
 * Referenced by: api.js (reads window.LEARNOVA_CONFIG.api),
 *                upload.html, dashboard.html, billing.html, module.html
 */

window.LEARNOVA_CONFIG = {

  // ── App Metadata ──
  stateVersion: '2026-04-14-empty-state', // Tracks config schema version for migrations
  appName: 'Learnova',

  // ── API / Backend Settings ──
  api: {
    baseUrl: 'http://127.0.0.1:8000',         // FastAPI backend origin
    questionCount: 6,                         // Default number of quiz questions per round
    followUpQuestionCount: 6                  // Default number of follow-up quiz questions
  },

  // ── Default User State ──
  // Hydrated into LEARNOVA_USER in app.js on page load.
  // Persisted/overwritten by localStorage values after login.
  user: {
    name: '',
    initials: '',
    email: '',
    pendingEmail: '',   // Set when user changes email; awaits verification
    avatarUrl: '',
    dob: '',            // Date of birth
    phone: '',
    password: '',
    passwordMask: '',   // Display-only mask string (e.g., "•••••••")
    tier: 'free'        // 'free' or 'pro', used to gate features
  },

  // ── Dashboard Defaults ──
  dashboard: {
    weeklyDocumentIncrease: 0,
    monthlyQuizCount: 0,
    scoreTrendLabel: 'Based on saved quiz history'
  },

  // ── Upload / File Constraints ──
  // Tier-based restrictions enforced client-side before API submission.
  upload: {
    supportedFileTypes: {
      free: ['.pdf', '.txt'],                        // Free tier: PDF and plain text only
      pro: ['.pdf', '.txt', '.pptx', '.ppt']         // Pro tier: also supports PowerPoint
    },
    maxFiles: {
      free: 1,    // Free users can upload one file at a time
      pro: 5      // Pro users can batch upload up to 5 files
    },
    maxFileSizeMb: 10,    // Maximum allowed file size in megabytes
    minTextLength: 200    // Minimum character count for text input validation
  },

  // ── Learning Module Defaults ──
  module: {
    calendars: [
      { name: 'Google Calendar', color: '#4A90D9' },
      { name: 'Apple Calendar', color: '#888888' },
      { name: 'Outlook', color: '#0F6E56' }
    ],
    resources: [],                                // Pre-populated resource links for modules
    apiBaseUrl: 'http://127.0.0.1:8000'
  },

  // ── History ──
  // In-memory mirror of ln_history from localStorage; populated at runtime.
  history: []
};
