// ── Learnova API client
// Mac 1 (172.16.40.120) — gpt-oss      — summarisation
// Mac 2 (172.16.40.122) — deepseek-r1  — quiz generation (background, polled)

const API_CONFIG   = APP_CONFIG.api || {};
const API_BASE_URL = (API_CONFIG.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');

const POLL_INTERVAL_MS = 3000;   // how often to check quiz status
const POLL_MAX_ATTEMPTS = 60;    // give up after 3 min (60 × 3s)

// ── Internal helpers ──────────────────────────────────────────────────────────
function normalizeQuestionCount(count) {
  const parsed = parseInt(count, 10);
  if (Number.isNaN(parsed)) return 6;
  return Math.min(8, Math.max(6, parsed));
}

function getApiProcessedTime() {
  return new Date().toLocaleTimeString('en-NZ', {
    hour: '2-digit', minute: '2-digit', hour12: true
  }).toLowerCase();
}

async function apiRequest(path, payload, method = 'POST') {
  let response;
  try {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (method !== 'GET') options.body = JSON.stringify(payload);
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (_) {
    throw new Error('Cannot reach the Learnova AI service. Start FastAPI and Ollama first.');
  }
  let data = {};
  try { data = await response.json(); } catch (_) {
    if (!response.ok) throw new Error('AI service returned an unreadable response.');
  }
  if (!response.ok) throw new Error(data.detail || 'AI service request failed.');
  return data;
}

// ── Formatters ────────────────────────────────────────────────────────────────
function formatSummaryForUI(summary) {
  return {
    pages:     `${summary.chunks_used || 1} ${summary.chunks_used === 1 ? 'section' : 'sections'} condensed`,
    title:     summary.summary_title,
    authors:   summary.authors || 'Unknown authors',
    body:      summary.body || [summary.overview],
    takeaways: summary.takeaways || [],
  };
}

function formatQuestionForUI(question) {
  return {
    q:           question.question,
    opts:        question.options,
    correct:     question.correct_index,
    explanation: question.explanation,
    topic:       question.topic,
  };
}

function buildInfoRows(meta) {
  return [
    ['File type',    meta.fileType    || 'TXT'],
    ['File size',    meta.sizeLabel   || 'Text input'],
    ['Pages',        String(meta.pageCount || 1)],
    ['Language',     meta.language    || 'English'],
    ['Processed at', meta.processedAt || getApiProcessedTime()],
  ];
}

function buildHistoryRecord({ id, title, meta, sourceText, summaryResponse, quizResponse, fileMeta }) {
  return {
    id, title, meta,
    fileType:     fileMeta.fileType  || 'TXT',
    pageCount:    fileMeta.pageCount || 1,
    infoRows:     buildInfoRows(fileMeta),
    sourceText,
    done:         false,
    summaryRaw:   summaryResponse,
    summary:      formatSummaryForUI(summaryResponse),
    topicTags:    summaryResponse.topics || [],
    quizData:     (quizResponse.questions || []).map(formatQuestionForUI),
    quizMode:     'initial',
    initialQuiz: {
      title:         quizResponse.title,
      questionCount: quizResponse.question_count,
      questions:     quizResponse.questions || [],
    },
    followUpQuiz:    null,
    learningModule:  null,
    progress:        null,
    strengths:       [],
    weaknesses:      [],
    weakTopics:      [],
    studyNext:       [],
    questions:       [],
  };
}

function applyAnalysisToRecord(record, analysis) {
  return {
    ...record,
    done:       true,
    score:      analysis.score_percent,
    correct:    analysis.correct_count,
    total:      analysis.total_questions,
    strengths:  analysis.strengths  || [],
    weaknesses: analysis.weaknesses || [],
    weakTopics: analysis.weak_topics || [],
    studyNext:  analysis.study_recommendations || [],
    analysis,
    questions: (analysis.reviewed_questions || []).map(item => ({
      q:           item.question,
      topic:       item.topic,
      correct:     item.is_correct,
      your:        item.user_answer,
      answer:      item.is_correct ? null : item.correct_answer,
      explanation: item.explanation,
    })),
  };
}

// ── Core: summarise + queue quiz in one call ──────────────────────────────────
/**
 * Calls /ai/summarize-and-queue-quiz.
 * Returns { summary, job_id } immediately — quiz is generating on Mac 2.
 *
 * @param {{ title: string, text: string }} payload
 * @returns {Promise<{ summary: object, job_id: string }>}
 */
async function summarizeAndQueueQuiz(payload) {
  const data = await apiRequest('/api/ai/summarize-and-queue-quiz', {
    title:          payload.title,
    text:           payload.text,
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.questionCount || 6),
    difficulty:     payload.difficulty || 'medium',
    exclude_questions: payload.exclude_questions || [],
  });
  return { summary: data.summary, job_id: data.job_id };
}

/**
 * Polls /ai/quiz-status/{job_id} every 3 seconds.
 *
 * @param {string} jobId
 * @param {{ onDone: (quiz) => void, onError: (msg) => void, onPending?: () => void }} callbacks
 */
function pollForQuiz(jobId, { onDone, onError, onPending }) {
  let attempts = 0;
  const interval = setInterval(async () => {
    attempts += 1;
    if (attempts > POLL_MAX_ATTEMPTS) {
      clearInterval(interval);
      onError('Quiz generation timed out. Check that Mac 2 (deepseek) is running.');
      return;
    }
    try {
      const data = await apiRequest(`/api/ai/quiz-status/${jobId}`, null, 'GET');
      if (data.status === 'done') {
        clearInterval(interval);
        onDone(data.result);
      } else if (data.status === 'error') {
        clearInterval(interval);
        onError(data.error || 'Quiz generation failed on Mac 2.');
      } else {
        // still pending
        if (typeof onPending === 'function') onPending();
      }
    } catch (err) {
      clearInterval(interval);
      onError(err.message || 'Lost connection while waiting for quiz.');
    }
  }, POLL_INTERVAL_MS);

  // Return a cancel function so callers can stop polling if needed
  return () => clearInterval(interval);
}

// ── Legacy single-call endpoints (still work) ─────────────────────────────────
async function summarizeDocument(payload) {
  return apiRequest('/api/ai/summarize', payload);
}

async function generateQuiz(payload) {
  return apiRequest('/api/ai/quiz', {
    ...payload,
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.questionCount || 6),
  });
}

async function analyzeQuizResults(payload) {
  return apiRequest('/api/ai/analyze-results', payload);
}

async function generateLearningModule(payload) {
  return apiRequest('/api/ai/learning-module', payload);
}

async function recommendResources(payload) {
  return apiRequest('/api/ai/recommend-resources', payload);
}

async function generateFollowUpQuiz(payload) {
  return apiRequest('/api/ai/follow-up-quiz', {
    ...payload,
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.followUpQuestionCount || 6),
  });
}

async function compareProgress(payload) {
  return apiRequest('/api/ai/compare-progress', payload);
}

// ── Export ────────────────────────────────────────────────────────────────────
window.LEARNOVA_API = {
  API_BASE_URL,
  normalizeQuestionCount,
  // New dual-Mac flow
  summarizeAndQueueQuiz,
  pollForQuiz,
  // Legacy (still work)
  summarizeDocument,
  generateQuiz,
  analyzeQuizResults,
  generateLearningModule,
  recommendResources,
  generateFollowUpQuiz,
  compareProgress,
  // Formatters
  formatSummaryForUI,
  formatQuestionForUI,
  buildHistoryRecord,
  applyAnalysisToRecord,
};
