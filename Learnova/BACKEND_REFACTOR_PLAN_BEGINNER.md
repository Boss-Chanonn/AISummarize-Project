# Backend Refactor Plan (Beginner Friendly)

The goal of this plan is to make the backend code clean, easy to read, and safe, without breaking the system.

## 1) Core Rules (Do Not Skip)

1. Do not change existing API endpoint paths.
2. Do not change existing response structure (existing keys must stay).
3. Work in small stages and test after every stage.
4. If a stage breaks something, roll back only that stage immediately.
5. Every function must have a short comment/docstring explaining its purpose.

## 2) Current Problems (From Real Code)

1. There is duplicated code in backend/routes/auth.py (duplicate functions and duplicate endpoints).
2. Many files do not have complete docstrings/comments for all functions.
3. Similar helper logic is repeated in multiple files (for example datetime/ObjectId serialization).
4. Some imports or constants may be unused.
5. Some functions are too long and difficult to read, and should be split into helper functions.

## 3) Comment Standard (Use One Style Across the Project)

### 3.1 Function Docstring (Required for Every Function)

Use this format:

```python
def example_function(param1: str, param2: int) -> dict:
    """What it does: one-line purpose of the function.

    Args:
        param1: Simple explanation for param1.
        param2: Simple explanation for param2.

    Returns:
        Simple explanation of the returned value.
    """
```

### 3.2 Inline Comments (Only for Complex Parts)

```python
# Calculate score based on the number of correct answers
score_pct = round((correct_count / total) * 100) if total > 0 else 0
```

Note: Do not comment every line. Add comments only where a beginner may get confused.

## 4) Stage Plan (Step-by-Step and Safe)

## STAGE B0 - Safety Baseline (Prevent Breakage Before Refactor)

Related files:
- backend/main.py
- backend/routes/*.py
- backend/middleware/*.py
- backend/services/*.py

Tasks:
1. Record baseline behavior of important APIs.
2. Create a smoke checklist for core flows.
3. Confirm server runs normally before making changes.

Minimum test checklist:
1. GET /api/health
2. POST /api/auth/register
3. POST /api/auth/login
4. GET /api/auth/profile (with token)
5. POST /api/upload
6. GET /api/history
7. POST /api/history/{id}/submit-quiz
8. GET /api/results
9. GET /api/billing/status
10. GET /api/admin/stats (admin token)

Exit criteria:
- All active endpoints still respond as expected.

## STAGE B1 - Clean Imports and Unused Code

Target files:
- backend/routes/auth.py
- backend/routes/billing.py
- backend/routes/sysadmin.py
- backend/models/user.py
- backend/main.py

Tasks:
1. Remove unused imports.
2. Remove unused variables.
3. Organize imports by group (stdlib -> third-party -> local).
4. Do not change business logic.

Exit criteria:
- Python compile check passes.
- Important endpoints still work the same.

## STAGE B2 - De-duplicate auth.py (High Priority)

Target files:
- backend/routes/auth.py

Tasks:
1. Remove duplicate functions (hash_password, verify_password, create_access_token).
2. Remove duplicate routes (health/register/login/logout/profile declared more than once).
3. Keep one complete route set that includes current fields (dob, phone, tier, role).
4. Add docstrings to every function.

Risk level:
- High (directly affects login/register).

Risk reduction steps:
1. Refactor in small blocks.
2. Test register/login/profile after each block.
3. Verify response format does not change.

Exit criteria:
- Only one auth route set remains.
- Login/logout/profile still works through frontend.

## STAGE B3 - Extract Shared Helpers

Target files:
- backend/routes/history.py
- backend/routes/content.py
- backend/routes/admin.py
- backend/routes/sysadmin.py
- (new file) backend/utils/serializers.py

Tasks:
1. Centralize shared conversion helpers (for example ObjectId/datetime to string).
2. Reduce repeated code across routes.
3. Add comments explaining shared helper behavior.

Exit criteria:
- Less duplicated code.
- Existing response behavior is unchanged.

## STAGE B4 - Group Functions by Domain

Target files:
- backend/routes/auth.py
- backend/routes/upload.py
- backend/routes/history.py
- backend/routes/content.py
- backend/routes/admin.py
- backend/routes/admin_stats.py
- backend/routes/billing.py
- backend/routes/sysadmin.py

Tasks:
1. Group functions in each file using clear section comments.
2. Example groups:
   - Validation Helpers
   - Auth Helpers
   - Read Endpoints
   - Write Endpoints
   - Admin Only Endpoints
3. Split very long functions into smaller helper functions (without changing output).

Exit criteria:
- A new reader can quickly understand file flow.
- No endpoint/response contract changes.

## STAGE B5 - Improve Error Handling Consistency

Target files:
- backend/routes/*.py

Tasks:
1. Standardize error message style.
2. Use clear and correct status code cases for 400/401/403/404/500.
3. Keep existing frontend-dependent messages where required.
4. Add comments explaining why each status code is used.

Exit criteria:
- Existing behavior still passes.
- Error paths are easier to understand.

## STAGE B6 - Upload and AI Service Readability

Target files:
- backend/routes/upload.py
- backend/services/ollama_service.py

Tasks:
1. Make upload flow clearly separated: input validation -> extraction -> AI -> save -> response.
2. Reduce upload_document size using helper functions.
3. Add docstrings to all helpers and API functions.
4. Comment important parts: fallback path, timeout, payload validation.

Exit criteria:
- Existing upload flow still works.
- AI fallback still works when AI is unavailable.

## STAGE B7 - Middleware and Security Clarity

Target files:
- backend/main.py
- backend/middleware/auth_middleware.py
- backend/middleware/security.py

Tasks:
1. Add clear comments for each middleware.
2. Make role checks easier to read.
3. Organize startup event and logging middleware sections.
4. Do not change security behavior.

Exit criteria:
- Auth and admin guards behave the same.
- Security headers are still returned.

## STAGE B8 - Final Cleanup and Documentation

Target files:
- All backend files
- README.md or a new backend coding-rules document

Tasks:
1. Final cleanup pass for remaining dead code.
2. Verify every function has comments/docstrings.
3. Document endpoint-to-file mapping.
4. Summarize what changed and any remaining risk.

Exit criteria:
- Backend is clearly easier to read.
- No broken endpoints.
- Local run/deploy works the same as before refactor.

## 5) Definition of Done (DoD)

Refactor is complete only when all items below are true:

1. Every function has a docstring.
2. Every file has section comments for function grouping.
3. Major duplicate code is removed (especially in auth.py).
4. No obvious unused import/dead code remains.
5. API behavior is unchanged (core endpoint and response contracts).
6. Important frontend flows still work.

## 6) Regression Test Checklist (Beginner Level)

Run this after each stage:

1. Open website and login works.
2. Document upload works.
3. Quiz submission and results page works.
4. Billing status page works.
5. Admin users/admin stats/admin history pages work with admin account.
6. Sysadmin health/logs pages work with system_admin account.

If any check fails: stop immediately and fix only the latest stage first.

## 7) Recommended Execution Order (Safest)

1. B0 -> B1 (low risk)
2. B2 (high risk, test frequently)
3. B3 -> B4 -> B5
4. B6 -> B7
5. B8 (final pass)

## 8) Critical Note: Do Not Break the Code

The main principle is: improve structure for readability, do not change system behavior.

For every change:
1. Make small changes.
2. Test immediately.
3. If something breaks, roll back only the latest change.
4. Avoid doing a huge multi-file refactor in one commit.
