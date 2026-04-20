/* ── Learnova Mock API ── */
/* Intercepts fetch() calls to /api/* and returns mock responses */
/* Remove this file when connecting to a real backend */

(function() {
  // Seed default user
  const MOCK_USERS_KEY = 'ln_mock_users';
  function getUsers() {
    return JSON.parse(localStorage.getItem(MOCK_USERS_KEY) || '[]');
  }
  function saveUsers(users) {
    localStorage.setItem(MOCK_USERS_KEY, JSON.stringify(users));
  }

  // Create default user if none exist
  if (getUsers().length === 0) {
    saveUsers([
      {
        name: 'Kunal Ahlawat',
        email: 'kunal@university.ac.nz',
        password: 'learnova123'
      }
    ]);
  }

  // No seeding — history starts empty until user summarises a document
  // One-time cleanup: remove old seeded history data from previous versions
  (function() {
    var h = JSON.parse(localStorage.getItem('ln_history') || '[]');
    if (h.length && h[0].title && h[0].title.indexOf('Zawacki') !== -1) {
      localStorage.removeItem('ln_history');
    }
  })();

  // Generate a fake JWT token (encodeURIComponent handles non-Latin1 chars like Thai)
  function generateToken(user) {
    const payload = btoa(unescape(encodeURIComponent(JSON.stringify({ name: user.name, email: user.email, iat: Date.now() }))));
    return 'mock.' + payload + '.signature';
  }

  // Route handlers
  const routes = {
    'POST /api/auth/register': function(body) {
      const { name, email, password } = body;
      if (!name || !email || !password) {
        return { status: 400, data: { message: 'All fields are required' } };
      }
      if (password.length < 8) {
        return { status: 400, data: { message: 'Password must be at least 8 characters' } };
      }
      const users = getUsers();
      if (users.find(u => u.email === email)) {
        return { status: 409, data: { message: 'Email already registered' } };
      }
      users.push({ name, email, password });
      saveUsers(users);
      return { status: 201, data: { message: 'Account created — please sign in' } };
    },

    'POST /api/auth/login': function(body) {
      const { email, password } = body;
      if (!email || !password) {
        return { status: 400, data: { message: 'Email and password are required' } };
      }
      const users = getUsers();
      const user = users.find(u => u.email === email && u.password === password);
      if (!user) {
        return { status: 401, data: { message: 'Invalid email or password' } };
      }
      const token = generateToken(user);
      return {
        status: 200,
        data: {
          token: token,
          user: { name: user.name, email: user.email }
        }
      };
    },

    'GET /api/user/profile': function(body, headers) {
      const token = (headers['Authorization'] || '').replace('Bearer ', '');
      if (!token) {
        return { status: 401, data: { message: 'Not authenticated' } };
      }
      try {
        const payload = JSON.parse(decodeURIComponent(escape(atob(token.split('.')[1]))));
        // Calculate stats dynamically from history
        var history = JSON.parse(localStorage.getItem('ln_history') || '[]');
        var totalDocs = history.length;
        var completedQuizzes = history.filter(function(h) { return h.done; });
        var quizCount = completedQuizzes.length;
        var avgScore = quizCount > 0
          ? Math.round(completedQuizzes.reduce(function(sum, h) { return sum + h.score; }, 0) / quizCount)
          : 0;

        // Build dynamic sub-labels
        var now = new Date();
        var weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        var monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        var newThisWeek = history.filter(function(h) {
          return h.uploadedAt && new Date(h.uploadedAt) >= weekAgo;
        }).length;
        var quizzesThisMonth = completedQuizzes.filter(function(h) {
          return h.uploadedAt && new Date(h.uploadedAt) >= monthAgo;
        }).length;

        return {
          status: 200,
          data: {
            name: payload.name,
            email: payload.email,
            documentsStudied: totalDocs,
            averageScore: avgScore,
            quizzesCompleted: quizCount,
            statSubs: [
              newThisWeek > 0 ? '+' + newThisWeek + ' this week' : 'No new uploads this week',
              quizCount > 0 ? 'Based on ' + quizCount + ' quiz' + (quizCount > 1 ? 'zes' : '') : 'No quizzes yet',
              quizzesThisMonth > 0 ? quizzesThisMonth + ' this month' : 'None this month'
            ]
          }
        };
      } catch (e) {
        return { status: 401, data: { message: 'Invalid token' } };
      }
    },

    'GET /api/history/recent': function(body, headers) {
      var history = JSON.parse(localStorage.getItem('ln_history') || '[]');
      return { status: 200, data: history.slice(0, 5) };
    },

    'GET /api/history': function(body, headers) {
      var history = JSON.parse(localStorage.getItem('ln_history') || '[]');
      return { status: 200, data: history };
    },

    'POST /api/upload': function(body) {
      var rawTitle = body.title || 'Uploaded Document';
      var title = rawTitle.replace(/\.[^.]+$/, '');
      var fileType = (body.fileType || 'TXT').toUpperCase();
      var pageCount = parseInt(body.pageCount) || 1;
      var wordEstimate = (pageCount * 350).toLocaleString();
      var now = new Date();
      var processedAt = now.toLocaleTimeString('en-NZ', { hour: '2-digit', minute: '2-digit', hour12: true }).toLowerCase();
      var yearStr = now.getFullYear().toString();
      var quizData = [
        { q: 'What is the primary focus or central argument of this document?', opts: ['Empirical measurement of outcomes', 'Theoretical critique of existing models', 'Systematic synthesis and analysis of prior work', 'Policy evaluation and reform recommendations'], correct: 2, explanation: 'The document takes a synthesis approach, drawing on prior research to build a central argument.' },
        { q: 'Which research methodology does this document primarily employ?', opts: ['Randomised controlled trial', 'Ethnographic fieldwork', 'Literature review and analytical framework', 'Longitudinal survey study'], correct: 2, explanation: 'A literature review and analytical framework are central to how the document builds its argument.' },
        { q: 'What type of evidence is most heavily used to support the main claims?', opts: ['Anecdotal case reports', 'Peer-reviewed academic studies', 'Government statistics only', 'Industry benchmarks and reports'], correct: 1, explanation: 'Peer-reviewed studies form the backbone of the evidential claims made throughout the document.' },
        { q: 'Which best describes the target audience of this document?', opts: ['General public readers', 'Academic researchers and practitioners', 'Policy makers only', 'First-year undergraduate students'], correct: 1, explanation: 'The technical language, academic framing, and citation style indicate this is aimed at researchers and informed practitioners.' },
        { q: 'What key gap or limitation is identified in the existing body of work?', opts: ['Lack of quantitative data', 'Under-representation of certain groups', 'Absence of sufficient longitudinal research', 'Overemphasis on theory over practice'], correct: 2, explanation: 'The document specifically notes that longitudinal evidence is underdeveloped in this field.' },
        { q: 'What does the document recommend for future research?', opts: ['Abandon current theoretical frameworks', 'Prioritise cross-disciplinary collaboration', 'Focus exclusively on quantitative approaches', 'Limit studies to single institutional contexts'], correct: 1, explanation: 'The document advocates for cross-disciplinary collaboration as the most promising avenue for advancing the field.' },
        { q: 'Which factor most significantly influences the outcomes discussed in this document?', opts: ['Funding levels', 'Institutional support and context', 'Individual participant motivation alone', 'Technological infrastructure availability'], correct: 1, explanation: 'Institutional support and context are identified as the dominant conditioning factor across the outcomes discussed.' },
        { q: 'What is the overall contribution of this document to its field?', opts: ['A definitive proof of a contested theory', 'A synthesised framework for understanding complex interactions', 'A replication study confirming existing findings', 'A full critique that discredits prior research'], correct: 1, explanation: 'The document contributes a synthesised framework that helps organise complex, sometimes contradictory findings in the field.' }
      ];
      return {
        status: 200,
        data: {
          title: title,
          fileType: fileType,
          pageCount: pageCount,
          meta: '.' + fileType.toLowerCase() + ' \u00b7 ' + pageCount + (pageCount === 1 ? ' page' : ' pages'),
          infoRows: [
            ['File type', fileType],
            ['Estimated words', wordEstimate],
            ['Pages', String(pageCount)],
            ['Language', 'English'],
            ['Processed at', processedAt]
          ],
          summary: {
            pages: pageCount + (pageCount === 1 ? ' page' : ' pages') + ' condensed',
            title: title,
            authors: 'AI-processed document \u00b7 ' + yearStr,
            body: [
              'This document has been processed by Learnova\u2019s AI engine. The content spans ' + pageCount + (pageCount === 1 ? ' page' : ' pages') + ' and covers a focused subject area with clear theoretical and empirical dimensions.',
              'The key themes identified include the methodology employed, the evidence base drawn upon, and the limitations acknowledged by the author(s). These form the basis for the comprehension quiz below.'
            ],
            takeaways: [
              'The document presents a structured argument supported by academic references and prior research.',
              'Core findings are framed within a broader context with implications for both theory and practice.',
              'Review this summary carefully \u2014 the quiz will test your understanding of the main claims and evidence.'
            ]
          },
          quizData: quizData,
          strengths: ['Research methodology', 'Evidence-based argument', 'Theoretical grounding'],
          weaknesses: ['Practical application', 'Longitudinal evidence'],
          studyNext: ['Cross-disciplinary research', 'Applied case studies', 'Longitudinal study design']
        }
      };
    },

    'POST /api/history/save': function(body) {
      var history = JSON.parse(localStorage.getItem('ln_history') || '[]');
      var maxId = history.reduce(function(max, h) { return Math.max(max, h.id || 0); }, 0);
      var newItem = {
        id: maxId + 1,
        title: body.title || 'Untitled',
        meta: body.meta || '',
        fileType: body.fileType || 'TXT',
        pageCount: body.pageCount || 1,
        score: body.score || 0,
        correct: body.correct || 0,
        total: body.total || 8,
        done: true,
        uploadedAt: new Date().toISOString(),
        summary: body.summary || {},
        strengths: body.strengths || [],
        weaknesses: body.weaknesses || [],
        studyNext: body.studyNext || [],
        questions: body.questions || [],
        quizFull: body.quizFull || []
      };
      history.unshift(newItem);
      localStorage.setItem('ln_history', JSON.stringify(history));
      return { status: 201, data: newItem };
    },

    'GET /api/results': function(body, headers, url) {
      var parts = (url || '').split('?');
      var params = new URLSearchParams(parts[1] || '');
      var id = parseInt(params.get('id') || '0');
      var history = JSON.parse(localStorage.getItem('ln_history') || '[]');
      var item = id ? history.find(function(h) { return h.id === id; }) : history[0];
      if (!item) {
        return { status: 404, data: { message: 'Result not found. Complete a quiz first.' } };
      }
      return { status: 200, data: item };
    },

    'GET /api/modules': function(body, headers, url) {
      var parts = (url || '').split('?');
      var params = new URLSearchParams(parts[1] || '');
      var historyId = parseInt(params.get('historyId') || '0');
      var history = JSON.parse(localStorage.getItem('ln_history') || '[]');
      var item = historyId ? history.find(function(h) { return h.id === historyId; }) : history[0];
      if (!item) {
        return { status: 404, data: { message: 'No module data found. Complete a quiz first.' } };
      }
      var weaknesses = item.weaknesses || [];
      var studyNext = item.studyNext || [];
      var topics = weaknesses.concat(studyNext).slice(0, 4);
      while (topics.length < 4) topics.push('study skills');
      var types = ['video', 'article', 'video', 'podcast'];
      var sources = [
        'MIT OpenCourseWare · YouTube',
        'Nature — npj Science of Learning',
        'EdSurge · Vimeo',
        'The EdTech Podcast · Spotify'
      ];
      var durations = ['18 min', '12 min read', '24 min', '38 min'];
      var tags = ['Watched', 'Peer-reviewed', 'Expert speaker', 'Transcript available'];
      var badges = [
        { 'class': 'badge-dim',  label: 'Done' },
        { 'class': 'badge-gold', label: 'Recommended' },
        { 'class': 'badge-green',label: 'New' },
        { 'class': 'badge-gold', label: 'Recommended' }
      ];
      var statuses = ['done', 'none', 'none', 'none'];
      var titleFns = [
        function(t) { return 'Understanding ' + t + ' in depth'; },
        function(t) { return 'The evidence on ' + t + ' in education'; },
        function(t) { return t.charAt(0).toUpperCase() + t.slice(1) + ' in practice: A guide'; },
        function(t) { return 'Rethinking ' + t + ' — experts discuss'; }
      ];
      var mainTopic = (weaknesses[0] || studyNext[0] || 'key concepts').toLowerCase();
      var totalMinutes = 92;
      return {
        status: 200,
        data: {
          historyId: item.id,
          docTitle: item.title,
          moduleTitle: mainTopic,
          description: 'Based on your quiz results, you missed questions about ' + mainTopic + '. These resources will help close that gap — estimated ' + totalMinutes + ' min total.',
          totalMinutes: totalMinutes,
          resourceCount: topics.length,
          progress: {
            done: 1,
            scheduled: 1,
            remaining: topics.length - 1,
            pct: Math.round(1 / topics.length * 100)
          },
          focusAreas: [
            { title: 'Rebuild the weak spot', body: 'Understand why ' + mainTopic + ' matters and what the research says.' },
            { title: 'Learn through mixed formats', body: 'Short article, practical video, and podcast pacing to keep the module engaging.' },
            { title: 'Leave with clearer recall', body: 'Use the scheduled resources to reinforce the same concept from multiple angles.' }
          ],
          resources: topics.map(function(topic, i) {
            return {
              id: i,
              type: types[i],
              title: titleFns[i](topic),
              source: sources[i],
              duration: durations[i],
              tag: tags[i],
              badge: badges[i],
              status: statuses[i]
            };
          })
        }
      };
    }
  };

  // Override fetch
  const originalFetch = window.fetch;
  window.fetch = function(url, options) {
    // Let real auth routes reach the backend — do not intercept them
    if (typeof url === 'string' && url.startsWith('/api/auth/')) {
      return originalFetch.apply(this, arguments);
    }
    if (typeof url === 'string' && url.startsWith('/api/')) {
      const method = (options && options.method || 'GET').toUpperCase();
      const routeKey = method + ' ' + url.split('?')[0];
      const handler = routes[routeKey];

      if (handler) {
        // Simulate network delay
        return new Promise(function(resolve) {
          setTimeout(function() {
            let body = {};
            if (options && options.body) {
              try { body = JSON.parse(options.body); } catch(e) {}
            }
            let headers = {};
            if (options && options.headers) {
              headers = options.headers;
            }
            const result = handler(body, headers, url);
            console.log('[Mock API]', routeKey, '→', result.status);
            resolve({
              ok: result.status >= 200 && result.status < 300,
              status: result.status,
              json: function() { return Promise.resolve(result.data); }
            });
          }, 400); // 400ms fake latency
        });
      }

      // Unhandled API route
      console.warn('[Mock API] No handler for:', routeKey);
      return Promise.resolve({
        ok: false,
        status: 404,
        json: function() { return Promise.resolve({ message: 'Endpoint not found' }); }
      });
    }

    // Non-API calls pass through to real fetch
    return originalFetch.apply(this, arguments);
  };

  console.log('[Mock API] Active — default user: kunal@university.ac.nz / learnova123');
})();
