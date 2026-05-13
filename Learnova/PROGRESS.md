# Learnova — AI Development Log
Last updated: 2026-05-01

## CRITICAL RULES FOR ALL AI AGENTS
1. NEVER modify .css files
2. NEVER modify frontend/js/app.js
3. NEVER modify frontend/js/animations.js
4. NEVER modify frontend/js/mock-api.js
5. NEVER hardcode credentials
6. ALWAYS read this file before starting
7. ALWAYS update this file after finishing
8. If unsure → STOP and ASK user
9. ALWAYS refactor code to beginner-friendly style: clear naming, simple flow, clean grouping, and easy-to-read structure

NOTE: .html files CAN be modified (owner approved on 2026-04-20)

## Project Overview
- Name     : Learnova
- Backend  : FastAPI + Python 3.11
- Frontend : HTML/CSS/JS (served via FastAPI)
- Database : MongoDB Atlas (cloud) — NOT local
- Auth     : JWT + bcrypt + token blocklist
- AI       : Ollama llama3:latest (with fallback if Ollama offline)
- Port     : 8000 (everything)

## User Roles
- user         → student, regular access (free/pro tier)
- admin        → manage users, view all history
- system_admin → full DB access, system logs

## API Field Formats — IMPORTANT
Quiz questions stored in MongoDB as:
  { q: "question text", opts: ["A","B","C","D"], correct: 0, explanation: "..." }
  NOTE: field is "q" (not "question"), "opts" (not "options")

History item key fields:
  _id: MongoDB ObjectId string (24-char hex)
  done: bool
  score: int (0-100) | null
  correct: int | null
  total: int
  fileType: "PDF"|"DOCX"|"PPTX"|"TXT"
  uploadedAt: ISO datetime string
  summary.body: array of 2 paragraph strings
  summary.takeaways: array of 3 strings
  analysis.strengths/weaknesses/recommendations/studyNext: arrays
  quizFull: array of 8 quiz question objects
  userAnswers: array of chosen option indices
  modules: array of 5 { title, type, url, description }

POST /api/upload (multipart/form-data):
  Fields: file (UploadFile) OR text_content (str) + title (str)
  Returns: historyId, summary{title,authors,pages,body[],takeaways[],strengths[],weaknesses[],studyNext[]}, quizData[], modules[]

POST /api/history/{id}/submit-quiz:
  Body: { answers: [0,2,1,...] } — array of chosen option indices
  Returns: { score, correct, total, _id, analysis }

## Completed Stages — AS OF 2026-04-22

### STAGE 1 — Core Setup ✅
### STAGE 1.1 — MongoDB Atlas + Docker ✅
### STAGE 1.2 — JWT Logout + Token Blocklist ✅
### STAGE 2 — Full Backend Rebuild ✅ (completed 2026-04-22)
Files: auth.py, user.py, upload.py, history.py, content.py, admin.py, sysadmin.py, main.py, ollama_service.py, models/user.py, requirements.txt
### STAGE 3 — Frontend Pages Updated ✅ (completed 2026-04-22)
Files: landing.html (DOB), upload.html (FormData + submit-quiz), results.html, history.html, module.html, index.html

## What works now (all verified 2026-04-22/23)
  ✅ POST /api/auth/register (DOB required)
  ✅ POST /api/auth/login (JWT 24h)
  ✅ POST /api/auth/logout (token blocklist)
  ✅ GET  /api/user/profile (documentsStudied, averageScore, quizzesCompleted, statSubs)
  ✅ POST /api/upload (FormData: file OR text_content; Ollama AI with fallback)
  ✅ GET  /api/history (all history, _id based)
  ✅ GET  /api/history/recent (last 5)
  ✅ GET  /api/history/{id} (single item)
  ✅ POST /api/history/{id}/submit-quiz (saves score, triggers AI analysis)
  ✅ DELETE /api/history/{id}
  ✅ GET  /api/results?id= (quiz results + analysis)
  ✅ GET  /api/modules?historyId= (5 AI-generated module links)
  ✅ GET  /api/admin/dashboard, /users, /history
  ✅ GET  /api/sysadmin/health, /stats, /logs
  ✅ Rate limiting (slowapi)
  ✅ Activity logging middleware
  ✅ Frontend: upload → quiz → results → modules full flow
  ✅ History page: Summary button + modal (re-read AI summaries)
  ✅ Ollama timeout: 300s (no more ReadTimeout on large documents)

## Still Missing / Not Yet Built
  ❌ admin.html frontend page (admin.py backend exists) → split into admin-users.html, admin-stats.html, admin-history.html ✅
  ✅ sysadmin.html frontend page → created as system-admin.html (2026-05-12)
  ✅ Plan & Billing page (Pro upgrade flow) — completed 2026-04-29
  ❌ PUT /api/auth/profile (update name/phone)
  ❌ PUT /api/auth/password (change password)

## Docker
  docker-compose up --build -d   ← use --build when requirements.txt changes
  Container: learnova-app-1 on port 8000
  Refresh PATH first: $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

## Change Log
| Date | Change | Reason |
|------|--------|---------|
| 2026-04-20 | Fixed duplicate MongoDB client | Stability |
| 2026-04-20 | Added role/tier to User model | RBAC |
| 2026-04-20 | Created auth_middleware.py | Route protection |
| 2026-04-20 | Registered SecurityHeadersMiddleware | Security |
| 2026-04-20 | Switched DB to MongoDB Atlas | Persistent cloud storage |
| 2026-04-20 | Added JWT blocklist (jti + MongoDB TTL) | Logout invalidates token |
| 2026-04-20 | Created POST /api/auth/logout | Secure server-side logout |
| 2026-04-22 | Added DOB field to register | Blueprint requirement |
| 2026-04-22 | Rewrote upload.py (FormData + text extraction) | Real file processing |
| 2026-04-22 | Rewrote ollama_service.py (full AI payload) | Summary+quiz+analysis+modules |
| 2026-04-22 | Rewrote history.py (submit-quiz + AI analysis) | Post-quiz personalization |
| 2026-04-22 | Created admin.py + sysadmin.py | Role-based management |
| 2026-04-22 | Updated main.py (all routers + slowapi + logging) | Complete API registration |
| 2026-04-22 | Updated frontend pages (results/history/module/index) | Match new API fields |
| 2026-04-22 | Fixed results.html (q.q + q.opts field names) | Was using wrong field names |
| 2026-04-22 | Fixed user.py datetime comparison (tz-aware) | Profile 500 error |
| 2026-04-23 | Added Summary button + modal to history.html | Re-read AI summaries from history |
| 2026-04-23 | Set OLLAMA_TIMEOUT_SECONDS=300 in .env | Prevent ReadTimeout on large documents |
| 2026-04-23 | Reduced ollama_service.py snippet to 1500 chars | Faster AI generation |
| 2026-04-29 | Added Payment & Billing feature | Pro upgrade flow |

---

### Payment & Billing Feature — 2026-04-29 ✅

**Files Created:**
- `backend/routes/billing.py`
- `frontend/billing.html`
- `frontend/payment.html`
- `frontend/confirm.html`
- `frontend/js/billing.js`

**Files Modified:**
- `backend/models/user.py` — added UpgradeRequest, PaymentConfirm, BillingResponse models; added datetime import
- `backend/main.py` — registered billing router at /api/billing

**API Routes Added:**
| Method | Route | Description |
|--------|-------|-------------|
| GET  | /api/billing/status   | Return current tier + plan info |
| POST | /api/billing/upgrade  | Return payment summary (pre-confirmation) |
| POST | /api/billing/confirm  | MOCK: upgrade user to Pro, store last4 only |
| POST | /api/billing/downgrade | Revert user to Free plan |

**Plan Details:**
| Plan | Price | Features |
|------|-------|----------|
| Free | $0/mo | PDF, Word, Text · 1 file at a time |
| Pro Monthly | $12.99/mo | +PowerPoint · 3 files simultaneously · Unlimited |
| Pro Yearly  | $99.99/yr | Same as monthly · Save 36% |

**User Flow:**
1. Click "Plan and billing" in sidebar account popup → `openSettings('plan')` (existing app.js) → OR navigate directly to `billing.html`
2. `billing.html` — choose Monthly/Yearly → click "Upgrade to Pro →" → sets sessionStorage → redirects to `payment.html`
3. `payment.html` — enter card details (mock) → validates → saves last4 + name to sessionStorage (full card NEVER stored) → redirects to `confirm.html`
4. `confirm.html` — shows order summary → "Confirm & Pay" → POST /api/billing/confirm → success notification → redirect to `dashboard.html`

**Security Notes:**
- Full card number is never stored (only last 4 digits)
- All billing endpoints require valid JWT via `get_current_user`  
- Payment is MOCK — no real payment gateway connected


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
| 2026-05-01 | Created admin-stats.html | Admin Stats Overview page |
| 2026-05-01 | Created backend/routes/admin_stats.py | 3 new admin stats API routes |
| 2026-05-01 | Registered admin_stats router in main.py | Routes active at /api/admin/stats |
| 2026-05-01 | Added Stats Overview link to admin-users.html sidebar | Navigation between admin pages |
| 2026-05-01 | Added User Detail Modal (row click) to admin-users.html | View user info inline |
| 2026-05-01 | Redesigned User Detail Modal — 2-tab layout | Tab 1: Profile (view/edit) | Tab 2: Account (role/tier/status/reset-pw) |
| 2026-05-01 | Added AdminUpdateProfile + AdminUpdateAccount models | backend/models/user.py |
| 2026-05-01 | Added PUT /api/admin/user/{id}/profile | Edit name, email, phone, dob |
| 2026-05-01 | Added PUT /api/admin/user/{id}/account | Change role, tier, status |
| 2026-05-13 | Added beginner-friendly refactor rule for all AI edits | Keep code simple, grouped, and readable |
| 2026-05-13 | Completed refactor Stage 9 (style.css Sections 1-4) | Added component grouping comments and readability formatting without behavior changes |
| 2026-05-13 | Completed refactor Stage 10 (animation + landing sections) | Added subgroup comments, score ring note, and responsive breakpoint documentation |
| 2026-05-13 | Completed refactor Stage 11 (admin CSS files) | Added section grouping and expanded compressed rules in admin-base.css, admin-stats.css, admin-users.css |
| 2026-05-13 | Completed refactor Stage 12 (upload.html inline JS) | Restored broken syntax, added JSDoc for 33 functions, grouped responsibilities, and improved readability without behavior changes |
| 2026-05-13 | Completed refactor Stage 13 (module/history/results inline JS) | Added JSDoc for 20 functions, renamed unclear helpers in history, and added phased section comments without behavior changes |
| 2026-05-13 | Completed refactor Stage 14 (dashboard/index inline JS) | Added named dashboard redirect handler, clarified greeting/meta helpers, and added phased comments/JSDoc without behavior changes |
| 2026-05-13 | Completed refactor Stage 15 (billing/payment/confirm inline JS) | Added JSDoc for billing flow functions, replaced anonymous payment input handlers with named functions, and added phased comments without behavior changes |
| 2026-05-13 | Completed refactor Stage 16 (admin-users inline JS) | Added JSDoc across admin user management functions, renamed openActionModal/switchUserDetailTab for clarity, and documented local helper duplicates without behavior changes |
| 2026-05-13 | Completed refactor Stage 17 (admin-stats/admin-history inline JS) | Added JSDoc for 16 functions, documented chart scaling behavior, and clarified local helper duplicates without behavior changes |
| 2026-05-01 | Added POST /api/admin/user/{id}/reset-password | Reset to Learnova@2026 |
| 2026-05-01 | Added status field to user register document | backend/routes/auth.py |

### Admin Stats Overview — 2026-05-01 ✅
Status: Completed

Files Created:
  - frontend/admin-stats.html
  - backend/routes/admin_stats.py

Files Modified:
  - backend/main.py (registered admin_stats router)
  - frontend/admin-users.html (added Stats Overview sidebar link)

API Routes Added:
  GET /api/admin/stats               — 6 summary stats from MongoDB
  GET /api/admin/stats/user-growth   — new users per day, last 30 days
  GET /api/admin/stats/upload-activity — uploads per day, last 30 days

Data Source: Real-time MongoDB (users_collection + history_collection)
Charts: Chart.js CDN — Line (user growth) + Bar (upload activity)
Cards: 6 total — Total Users, Active Users, Pro Users, Total Uploads, Quizzes, Avg Score
Active Users: users who uploaded in the last 30 days (distinct userId in history)
Auth: JWT guard + role revalidation via /api/auth/profile on every page load

## Next Steps for Next AI Agent
1. Read this PROGRESS.md first
2. Read mock-api.js to understand API format
3. Build Stage 2: GET /api/user/profile
   Returns: name, email, documentsStudied,
            averageScore, quizzesCompleted, statSubs
4. Then Stage 3: POST /api/upload
   Accept PDF or text, return mock AI summary
5. Update PROGRESS.md when done
