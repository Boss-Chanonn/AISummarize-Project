window.LEARNOVA_CONFIG = {
  stateVersion: '2026-04-14-empty-state',
  appName: 'Learnova',
  api: {
    baseUrl: 'http://127.0.0.1:8000',
    questionCount: 6,
    followUpQuestionCount: 6
  },
  user: {
    name: '',
    initials: '',
    email: '',
    pendingEmail: '',
    avatarUrl: '',
    dob: '',
    phone: '',
    password: '',
    passwordMask: '',
    tier: 'free'
  },
  dashboard: {
    weeklyDocumentIncrease: 0,
    monthlyQuizCount: 0,
    scoreTrendLabel: 'Based on saved quiz history'
  },
  upload: {
    supportedFileTypes: {
      free: ['.pdf', '.txt'],
      pro: ['.pdf', '.txt', '.pptx', '.ppt']
    },
    maxFiles: {
      free: 1,
      pro: 5
    },
    maxFileSizeMb: 10,
    minTextLength: 200
  },
  module: {
    calendars: [
      { name: 'Google Calendar', color: '#4A90D9' },
      { name: 'Apple Calendar', color: '#888888' },
      { name: 'Outlook', color: '#0F6E56' }
    ],
    resources: [],
    apiBaseUrl: 'http://127.0.0.1:8000'
  },
  history: []
};
