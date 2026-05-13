# Backend Endpoint Map

Purpose: provide a quick backend ownership map so future refactors, bug fixes, and new chat sessions can find the right file fast.

## App Entry and Shared Layers

| Area | File | Responsibility |
|------|------|----------------|
| App bootstrap | `backend/main.py` | FastAPI app setup, middleware registration, router registration, health route, startup checks, frontend static hosting |
| Database | `backend/database/db.py` | MongoDB client setup and shared collections |
| Auth middleware | `backend/middleware/auth_middleware.py` | JWT decoding, blocklist validation, current-user/admin/system-admin guards |
| Security middleware | `backend/middleware/security.py` | Security headers and no-cache headers for frontend assets |
| Shared API errors | `backend/utils/api_errors.py` | Consistent JSON error responses with `message` field |
| Shared serializers | `backend/utils/serializers.py` | MongoDB `_id` and datetime serialization helpers |
| AI service | `backend/services/ollama_service.py` | Ollama prompt building, JSON extraction, payload normalization, quiz analysis |

## Route Ownership

| Prefix / Endpoint Area | File | Main Responsibility |
|------------------------|------|---------------------|
| `/api/auth/*` | `backend/routes/auth.py` | Register, login, logout, profile read/update, password change |
| `/api/user/*` | `backend/routes/user.py` | Dashboard profile statistics for current user |
| `/api/upload` | `backend/routes/upload.py` | File/text intake, extraction, AI generation, history save, upload response |
| `/api/history/*` | `backend/routes/history.py` | History list/detail, quiz submission, history deletion |
| `/api/results` and `/api/modules` | `backend/routes/content.py` | Quiz results and generated learning modules |
| `/api/admin/*` (user/account/history) | `backend/routes/admin.py` | Admin user management, admin history, account mutations, admin dashboard |
| `/api/admin/stats*` | `backend/routes/admin_stats.py` | Admin overview cards and chart datasets |
| `/api/sysadmin/*` | `backend/routes/sysadmin.py` | System health, system totals, logs, DB collection viewer, destructive DB actions |
| `/api/billing/*` | `backend/routes/billing.py` | Billing status, upgrade summary, confirm payment, downgrade |

## Data Models

| File | Purpose |
|------|---------|
| `backend/models/user.py` | Pydantic request and response models for auth, admin account edits, and billing |

## Suggested Debug Path

1. Auth or role issue: start with `backend/middleware/auth_middleware.py`, then inspect the owning route file.
2. Route returns wrong JSON shape: inspect the owning route file, then check `backend/utils/serializers.py` and `backend/utils/api_errors.py`.
3. Upload or AI issue: inspect `backend/routes/upload.py`, then `backend/services/ollama_service.py`.
4. Admin/system admin issue: inspect `backend/routes/admin.py`, `backend/routes/admin_stats.py`, or `backend/routes/sysadmin.py` depending on the URL prefix.
5. Startup or middleware issue: inspect `backend/main.py`, then the middleware files.

## Notes for Future Refactors

- Keep existing endpoint paths stable unless frontend pages are updated together.
- Preserve response key names used by the frontend, especially `message`, `_id`, `quizFull`, and billing fields.
- `backend/routes/sysadmin.py` keeps one legacy `error` key in the collection-view endpoint for compatibility.
- Protected-route regression can be checked quickly with tokenized smoke tests against user, admin, and system_admin accounts.
