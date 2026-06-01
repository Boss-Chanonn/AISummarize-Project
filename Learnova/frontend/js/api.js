/**
 * ── Learnova API Layer ──
 *
 * Central communication module between the frontend and the FastAPI backend.
 * All AI endpoints (summarize, quiz, analysis, learning module, etc.) are
 * called through this file.
 *
 * Exposes:
 *   - window.LEARNOVA_API — object holding every public function
 *   - API_BASE_URL        — resolved backend URL with trailing slash removed
 *
 * Dependencies:
 *   - config.js (window.LEARNOVA_CONFIG.api) for base URL and default question counts
 *   - app.js   (calls these functions from upload.html, quiz.html, dashboard.html, etc.)
 */

// ── Configuration ──

// Read API settings from the global config object (set in config.js).
const API_CONFIG = (window.LEARNOVA_CONFIG || window.APP_CONFIG || {}).api || {};

// Resolve the base backend URL and strip any trailing slash for consistent path joining.
const API_BASE_URL = (API_CONFIG.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');

// ── Helper Functions ──

/**
 * Clamp a requested question count between 6 and 8.
 * Falls back to 6 if the input is not a valid number.
 *
 * Used by generateQuiz() and generateFollowUpQuiz() to enforce
 * a reasonable question range regardless of what the caller sends.
 *
 * @param {number|string} count - Desired question count
 * @returns {number} A whole number in [6, 8]
 */
function normalizeQuestionCount(count) {
  const parsed = parseInt(count, 10);
  if (Number.isNaN(parsed)) return 6;
  return Math.min(8, Math.max(6, parsed));
}

/**
 * Generate a human-readable "processed at" timestamp in NZ locale format.
 * Used as a fallback when the backend does not provide a processedAt value.
 *
 * @returns {string} e.g. "10:32 am"
 */
function getApiProcessedTime() {
  return new Date().toLocaleTimeString('en-NZ', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }).toLowerCase();
}

// ── Core API Request ──

/**
 * Low-level fetch wrapper shared by every AI endpoint.
 *
 * Sends a POST with JSON body to the given backend path.
 * Throws user-friendly error messages for network failures,
 * non-OK status codes, or unparseable responses.
 *
 * @param {string} path   - URL path relative to API_BASE_URL (e.g. "/api/ai/summarize")
 * @param {object} payload - JSON-serialisable request body
 * @returns {Promise<object>} Parsed JSON response from the backend
 * @throws {Error} If the backend is unreachable, returns a non-2xx status,
 *                 or sends unreadable content.
 */
async function apiRequest(path, payload) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
  } catch (_) {
    // Network-level failure (e.g. server is down, CORS error, DNS failure).
    throw new Error('Cannot reach the Learnova AI service. Start FastAPI and Ollama first.');
  }

  let data = {};
  try {
    data = await response.json();
  } catch (_) {
    // Response arrived but body is not valid JSON.
    if (!response.ok) throw new Error('AI service returned an unreadable response.');
  }

  // Backend returned an HTTP error (4xx / 5xx) with a detail message.
  if (!response.ok) {
    throw new Error(data.detail || 'AI service request failed.');
  }
  return data;
}

// ── Data Formatting Helpers ──

/**
 * Convert a raw summarisation API response into the shape expected by
 * dashboard.js, upload.js, and the history detail modal.
 *
 * Called by: buildHistoryRecord()
 *
 * @param {object} summary - Raw summarisation result from the backend
 * @returns {{pages, title, authors, body, takeaways}}
 */
function formatSummaryForUI(summary) {
  return {
    pages: `${summary.chunks_used || 1} ${summary.chunks_used === 1 ? 'section' : 'sections'} condensed`,
    title: summary.summary_title,
    authors: summary.authors || 'Unknown authors',
    body: summary.body || [summary.overview],    // Overview is the fallback for paragraph text
    takeaways: summary.takeaways || []
  };
}

/**
 * Convert a raw quiz question object into a frontend-friendly shape.
 *
 * Called by: buildHistoryRecord() (via .map(formatQuestionForUI))
 *
 * @param {object} question - Raw question from the API
 * @returns {{q, opts, correct, explanation, topic}}
 */
function formatQuestionForUI(question) {
  return {
    q: question.question,
    opts: question.options,             // Array of answer choices
    correct: question.correct_index,    // Index of the correct option
    explanation: question.explanation,
    topic: question.topic
  };
}

/**
 * Build the "info rows" array used by summary cards and history items.
 * Each row is a [label, value] pair rendered in the document metadata section.
 *
 * Called by: buildHistoryRecord()
 *
 * @param {object} meta - File/document metadata from the upload flow
 * @returns {Array<[string, string]>}
 */
function buildInfoRows(meta) {
  return [
    ['File type', meta.fileType || 'TXT'],
    ['File size', meta.sizeLabel || 'Text input'],
    ['Pages', String(meta.pageCount || 1)],
    ['Language', meta.language || 'English'],
    ['Processed at', meta.processedAt || getApiProcessedTime()]
  ];
}

/**
 * Assemble a full history record object from the results of summary + quiz API calls.
 * This record is stored in localStorage (ln_history) and rendered by history.js.
 *
 * The record starts with `done: false`; it is marked `done: true` only after
 * applyAnalysisToRecord() merges in quiz analysis results.
 *
 * Called from: upload.js after both /api/ai/summarize and /api/ai/quiz complete.
 *
 * @param {object} params
 * @param {string} params.id             - Unique record identifier (typically a UUID)
 * @param {string} params.title          - Document title
 * @param {object} params.meta           - Document metadata
 * @param {string} params.sourceText     - Original extracted text
 * @param {object} params.summaryResponse - Raw response from /api/ai/summarize
 * @param {object} params.quizResponse    - Raw response from /api/ai/quiz
 * @param {object} params.fileMeta        - File-level metadata (type, size, pages, etc.)
 * @returns {object} A fully-shaped history record
 */
function buildHistoryRecord({
  id,
  title,
  meta,
  sourceText,
  summaryResponse,
  quizResponse,
  fileMeta
}) {
  return {
    id,
    title,
    meta,
    fileType: fileMeta.fileType || 'TXT',
    pageCount: fileMeta.pageCount || 1,
    infoRows: buildInfoRows(fileMeta),
    sourceText,
    done: false,                                  // Set to true after analysis completes
    summaryRaw: summaryResponse,
    summary: formatSummaryForUI(summaryResponse),
    topicTags: summaryResponse.topics || [],
    quizData: (quizResponse.questions || []).map(formatQuestionForUI),
    quizMode: 'initial',
    initialQuiz: {
      title: quizResponse.title,
      questionCount: quizResponse.question_count,
      questions: quizResponse.questions || []
    },
    followUpQuiz: null,   // Populated when the user requests a follow-up round
    learningModule: null,
    progress: null,
    // The following fields are filled in by applyAnalysisToRecord():
    strengths: [],
    weaknesses: [],
    weakTopics: [],
    studyNext: [],
    questions: []
  };
}

/**
 * Merge quiz analysis results (from /api/ai/analyze-results) into an existing
 * history record. Marks the record as `done: true` and enriches it with
 * score, strengths/weaknesses, study recommendations, and per-question review data.
 *
 * Called from: quiz.js after the user completes a quiz and the analysis returns.
 *
 * @param {object} record    - A history record previously built by buildHistoryRecord()
 * @param {object} analysis  - Raw response from /api/ai/analyze-results
 * @returns {object} The record merged with all analysis fields (shallow-copied via spread)
 */
function applyAnalysisToRecord(record, analysis) {
  return {
    ...record,
    done: true,
    score: analysis.score_percent,
    correct: analysis.correct_count,
    total: analysis.total_questions,
    strengths: analysis.strengths || [],
    weaknesses: analysis.weaknesses || [],
    weakTopics: analysis.weak_topics || [],
    studyNext: analysis.study_recommendations || [],
    analysis,
    // Re-shape reviewed questions into the format used by renderQuestionListMarkup() in app.js
    questions: (analysis.reviewed_questions || []).map(item => ({
      q: item.question,
      topic: item.topic,
      correct: item.is_correct,
      your: item.user_answer,
      answer: item.is_correct ? null : item.correct_answer,  // Omit correct answer when user already got it right
      explanation: item.explanation
    }))
  };
}

// ── AI Endpoint Functions ──
// Each wraps apiRequest() with a specific endpoint path.
// These are the primary functions called from page-level scripts (upload.js, quiz.js, dashboard.js, etc.).

/**
 * Send document text for AI summarisation.
 * Called from upload.js after document upload/preprocessing completes.
 */
async function summarizeDocument(payload) {
  return apiRequest('/api/ai/summarize', payload);
}

/**
 * Generate a multiple-choice quiz from document content.
 * Question count is normalised via normalizeQuestionCount().
 * Called from upload.js or quiz.js at the start of a quiz session.
 */
async function generateQuiz(payload) {
  return apiRequest('/api/ai/quiz', {
    ...payload,
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.questionCount || 6)
  });
}

/**
 * Submit user answers for AI-powered performance analysis.
 * Called from quiz.js after the user submits the quiz.
 */
async function analyzeQuizResults(payload) {
  return apiRequest('/api/ai/analyze-results', payload);
}

/**
 * Generate a structured learning module from document content + quiz results.
 * Called from module.html or quiz.js for the "View learning module" flow.
 */
async function generateLearningModule(payload) {
  return apiRequest('/api/ai/learning-module', payload);
}

/**
 * Fetch recommended learning resources based on user performance.
 * Called from dashboard.js or module.html.
 */
async function recommendResources(payload) {
  return apiRequest('/api/ai/recommend-resources', payload);
}

/**
 * Generate a follow-up quiz focused on weak topics identified during analysis.
 * Called from quiz.js when the user requests another round.
 */
async function generateFollowUpQuiz(payload) {
  return apiRequest('/api/ai/follow-up-quiz', {
    ...payload,
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.followUpQuestionCount || 6)
  });
}

/**
 * Compare user's progress across multiple quiz attempts.
 * Called from dashboard.js for the progress/comparison chart.
 */
async function compareProgress(payload) {
  return apiRequest('/api/ai/compare-progress', payload);
}

// ── Public API ──
// Attach all functions to window.LEARNOVA_API so page-level scripts
// (upload.js, quiz.js, dashboard.js, etc.) can call them directly.
window.LEARNOVA_API = {
  API_BASE_URL,
  normalizeQuestionCount,
  summarizeDocument,
  generateQuiz,
  analyzeQuizResults,
  generateLearningModule,
  recommendResources,
  generateFollowUpQuiz,
  compareProgress,
  formatSummaryForUI,
  formatQuestionForUI,
  buildHistoryRecord,
  applyAnalysisToRecord
};