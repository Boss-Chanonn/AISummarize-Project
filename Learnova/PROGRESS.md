# Learnova — AI Development Log
Last updated: 2026-04-20

## CRITICAL RULES FOR ALL AI AGENTS
1. NEVER modify .css files
2. NEVER modify frontend/js/app.js
3. NEVER modify frontend/js/animations.js
4. NEVER modify frontend/js/mock-api.js
5. NEVER hardcode credentials
6. ALWAYS read this file before starting
7. ALWAYS update this file after finishing
8. If unsure → STOP and ASK user

NOTE: .html files CAN be modified (owner approved on 2026-04-20)

## Project Overview
- Name     : Learnova
- Backend  : FastAPI + Python 3.11
- Frontend : HTML/CSS/JS (served via FastAPI)
- Database : MongoDB Atlas (cloud) — NOT local
- Auth     : JWT + bcrypt + token blocklist
- AI       : Mock now → Kunal adds Groq later
- Port     : 8000 (everything)

## User Roles
- user         → student, regular access
- admin        → manage users, view all history
- system_admin → full DB access, system logs

## API Format — mock-api.js is the source of truth
Frontend mock-api.js defines EXACT response format.
Backend must match it precisely.

Key formats:
POST /api/upload response must include:
  studyNext (NOT recommendations)
  quizData with: q, opts, correct (index), explanation

POST /api/history/save receives:
  title, meta, fileType, pageCount
  score, correct, total, done
  summary, strengths, weaknesses
  studyNext, questions, quizFull

## Completed Stages

### STAGE 1 — Core Setup (2026-04-20)
Files modified:
  - requirements.txt (added PyPDF2, httpx, boto3)
  - backend/database/db.py (single client, all collections)
  - backend/models/user.py (added role, tier fields)
  - backend/middleware/auth_middleware.py (created)
  - backend/routes/auth.py (added role/tier, profile route)
  - backend/main.py (fixed duplicate client, registered middleware)
  - .env.example (updated)

What works now:
  ✅ POST /api/auth/register (saves role, tier)
  ✅ POST /api/auth/login (JWT includes role, id)
  ✅ GET  /api/auth/profile (protected route)
  ✅ GET  /api/health
  ✅ SecurityHeadersMiddleware registered
  ✅ Single MongoDB client
  ✅ JWT verification dependency ready

### STAGE 1.1 — Infrastructure & Security Fixes (2026-04-20)
Files modified:
  - docker-compose.yml (removed local MongoDB service, added PYTHONUNBUFFERED=1)
  - .env (switched MONGO_URL to MongoDB Atlas, DATABASE_NAME=learnova)

What works now:
  ✅ App connects to MongoDB Atlas (cloud) — verified with ping
  ✅ No local MongoDB container — only learnova-app-1 runs
  ✅ All data saved to Atlas (verified by querying live)
  ✅ Docker logs visible in terminal (PYTHONUNBUFFERED=1)

### STAGE 1.2 — JWT Logout + Token Invalidation (2026-04-20)
Files modified:
  - backend/database/db.py (added token_blocklist_collection)
  - backend/routes/auth.py (added jti to token payload, added POST /logout route)
  - backend/middleware/auth_middleware.py (checks blocklist on every request)
  - backend/main.py (creates TTL index on startup for auto-cleanup)
  - frontend/js/auth-logout.js (created — calls backend logout before redirect)
  - frontend/index.html (added auth-logout.js script tag)
  - frontend/history.html (added auth-logout.js script tag)
  - frontend/upload.html (added auth-logout.js script tag)
  - frontend/module.html (added auth-logout.js script tag)
  - frontend/results.html (added auth-logout.js script tag)

How it works:
  - Every JWT now has a unique jti (UUID) in its payload
  - POST /logout stores jti + expiry into token_blocklist collection in Atlas
  - get_current_user checks blocklist on every protected request
  - MongoDB TTL index auto-deletes expired blocklist entries (expireAfterSeconds=0)
  - Frontend Sign out button calls /api/auth/logout then clears localStorage
  - If network fails → still clears localStorage and redirects (safe fallback)

What works now:
  ✅ POST /api/auth/logout (invalidates token server-side)
  ✅ Using invalidated token → 401 "Token has been invalidated"
  ✅ Atlas token_blocklist collection auto-cleaned by TTL index
  ✅ Sign out button in sidebar calls real backend (all pages)

## Still Missing
  ❌ GET  /api/user/profile (dashboard stats)
  ❌ POST /api/upload (PDF + text + mock AI)
  ❌ POST /api/history/save
  ❌ GET  /api/history
  ❌ GET  /api/history/recent
  ❌ GET  /api/results?id=X
  ❌ GET  /api/modules?historyId=X
  ❌ Admin routes
  ❌ Google Calendar routes

## Change Log
| Date | Change | Reason |
|------|--------|---------|
| 2026-04-20 | Fixed duplicate MongoDB client | Stability |
| 2026-04-20 | Added role/tier to User model | RBAC |
| 2026-04-20 | Created auth_middleware.py | Route protection |
| 2026-04-20 | Registered SecurityHeadersMiddleware | Security |
| 2026-04-20 | Added /api/auth/profile route | Frontend needs it |
| 2026-04-20 | Switched DB to MongoDB Atlas | Persistent cloud storage |
| 2026-04-20 | Removed local MongoDB container | Eliminate dual-DB confusion |
| 2026-04-20 | Added PYTHONUNBUFFERED=1 to docker-compose | Fix log buffering |
| 2026-04-20 | Added JWT blocklist (jti + MongoDB TTL) | Logout invalidates token |
| 2026-04-20 | Created POST /api/auth/logout | Secure server-side logout |
| 2026-04-20 | Created auth-logout.js | Connect Sign out button to backend |
| 2026-04-20 | Added auth-logout.js to 5 HTML pages | All pages now logout properly |

## Next Steps for Next AI Agent
1. Read this PROGRESS.md first
2. Read mock-api.js to understand API format
3. Build Stage 2: GET /api/user/profile
   Returns: name, email, documentsStudied,
            averageScore, quizzesCompleted, statSubs
4. Then Stage 3: POST /api/upload
   Accept PDF or text, return mock AI summary
5. Update PROGRESS.md when done
