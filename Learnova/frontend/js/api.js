const API_CONFIG = (window.LEARNOVA_CONFIG || window.APP_CONFIG || {}).api || {};
const API_BASE_URL = (API_CONFIG.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');

function normalizeQuestionCount(count) {
  const parsed = parseInt(count, 10);
  if (Number.isNaN(parsed)) return 6;
  return Math.min(8, Math.max(6, parsed));
}

function getApiProcessedTime() {
  return new Date().toLocaleTimeString('en-NZ', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }).toLowerCase();
}

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
    throw new Error('Cannot reach the Learnova AI service. Start FastAPI and Ollama first.');
  }

  let data = {};
  try {
    data = await response.json();
  } catch (_) {
    if (!response.ok) throw new Error('AI service returned an unreadable response.');
  }

  if (!response.ok) {
    throw new Error(data.detail || 'AI service request failed.');
  }
  return data;
}

function formatSummaryForUI(summary) {
  return {
    pages: `${summary.chunks_used || 1} ${summary.chunks_used === 1 ? 'section' : 'sections'} condensed`,
    title: summary.summary_title,
    authors: summary.authors || 'Unknown authors',
    body: summary.body || [summary.overview],
    takeaways: summary.takeaways || []
  };
}

function formatQuestionForUI(question) {
  return {
    q: question.question,
    opts: question.options,
    correct: question.correct_index,
    explanation: question.explanation,
    topic: question.topic
  };
}

function buildInfoRows(meta) {
  return [
    ['File type', meta.fileType || 'TXT'],
    ['File size', meta.sizeLabel || 'Text input'],
    ['Pages', String(meta.pageCount || 1)],
    ['Language', meta.language || 'English'],
    ['Processed at', meta.processedAt || getApiProcessedTime()]
  ];
}

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
    done: false,
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
    followUpQuiz: null,
    learningModule: null,
    progress: null,
    strengths: [],
    weaknesses: [],
    weakTopics: [],
    studyNext: [],
    questions: []
  };
}

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
    questions: (analysis.reviewed_questions || []).map(item => ({
      q: item.question,
      topic: item.topic,
      correct: item.is_correct,
      your: item.user_answer,
      answer: item.is_correct ? null : item.correct_answer,
      explanation: item.explanation
    }))
  };
}

async function summarizeDocument(payload) {
  return apiRequest('/api/ai/summarize', payload);
}

async function generateQuiz(payload) {
  return apiRequest('/api/ai/quiz', {
    ...payload,
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.questionCount || 6)
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
    question_count: normalizeQuestionCount(payload.question_count || API_CONFIG.followUpQuestionCount || 6)
  });
}

async function compareProgress(payload) {
  return apiRequest('/api/ai/compare-progress', payload);
}

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