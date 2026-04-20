# Learnova — AI Development Log
Last updated: 2026-04-20

## CRITICAL RULES FOR ALL AI AGENTS
1. NEVER modify .html files
2. NEVER modify .css files
3. NEVER modify frontend/js/app.js
4. NEVER modify frontend/js/animations.js
5. NEVER modify frontend/js/mock-api.js
6. NEVER hardcode credentials
7. ALWAYS read this file before starting
8. ALWAYS update this file after finishing
9. If unsure → STOP and ASK user

## Project Overview
- Name     : Learnova
- Backend  : FastAPI + Python 3.11
- Frontend : HTML/CSS/JS (served via FastAPI)
- Database : MongoDB via Docker (port 27017)
- Auth     : JWT + bcrypt
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
|------|--------|--------|
| 2026-04-20 | Fixed duplicate MongoDB client | Stability |
| 2026-04-20 | Added role/tier to User model | RBAC |
| 2026-04-20 | Created auth_middleware.py | Route protection |
| 2026-04-20 | Registered SecurityHeadersMiddleware | Security |
| 2026-04-20 | Added /api/auth/profile route | Frontend needs it |

## Next Steps for Next AI Agent
1. Read this PROGRESS.md first
2. Read mock-api.js to understand API format
3. Build Stage 2: GET /api/user/profile
   Returns: name, email, documentsStudied,
            averageScore, quizzesCompleted, statSubs
4. Then Stage 3: POST /api/upload
   Accept PDF or text, return mock AI summary
5. Update PROGRESS.md when done
