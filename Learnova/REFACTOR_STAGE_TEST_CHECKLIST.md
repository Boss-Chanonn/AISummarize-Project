# LEARNOVA REFACTOR - STAGE TEST CHECKLIST

Purpose: prevent regressions while executing the 17-stage refactor plan.
Rule: complete one stage at a time, run this checklist, then move to next stage.

---

## 1) Pre-Stage Baseline (run before each stage)

- [ ] Working tree is clean or only contains intended files for this stage.
- [ ] App starts successfully.
- [ ] Current stage scope and target files are confirmed.
- [ ] A short rollback point exists (commit or stash with clear message).

Recommended startup:

```powershell
Set-Location E:\AISummarize-Project\Learnova
docker compose up --build
```

---

## 2) Core Smoke Test Pack (run after every stage)

### Auth and Routing
- [ ] Open index page and login works.
- [ ] User role routing works:
  - user -> dashboard
  - admin -> admin users
  - system_admin -> system admin
- [ ] Logout works and protected pages redirect correctly.

### User Flow (client)
- [ ] Dashboard loads stats and recent activity.
- [ ] Upload page accepts file/text and process button state is correct.
- [ ] Quiz flow works: start, answer, skip, finish.
- [ ] History list loads; detail modal opens and closes.
- [ ] Results page renders score and details.

### Billing Flow
- [ ] Billing page loads current plan status.
- [ ] Payment form validation works (number, expiry, cvv).
- [ ] Confirm page loads order and submit flow completes.

### Admin Flow
- [ ] Admin Users table loads.
- [ ] Filter, sort, pagination, and row selection work.
- [ ] Action modals open/close and execute correctly.
- [ ] Admin Stats charts/cards load without errors.
- [ ] Admin History list and summary modal work.

### System Admin Flow
- [ ] System Overview shows service status, stats, and API health.
- [ ] User Control filters and actions work.
- [ ] Database Manager collections open and documents render.
- [ ] Security Center tabs render and export works.

### UI/UX Sanity
- [ ] No major layout break on desktop.
- [ ] No major layout break on mobile width.
- [ ] Modals and toasts still appear and close correctly.

### Console and Network
- [ ] Browser console has no new errors.
- [ ] No failed critical API requests in network panel.

---

## 3) Stage-Specific Gates

## Stage 1-4 (app.js user helpers, toast/sidebar, settings/profile, history modals)
- [ ] All renamed/extracted helpers are still called from original entry points.
- [ ] History detail and split modals render same content as before.
- [ ] Toast behavior is unchanged (position, icon, timeout).

## Stage 5 (app.js system admin section) - high risk
- [ ] All system admin sections switch correctly.
- [ ] Role checks still block non-system_admin users.
- [ ] User actions (role change, reset password, delete) behave correctly.
- [ ] Database and security panels still render with expected defaults.
- [ ] Export logs to CSV still downloads valid file.

## Stage 6 (animations.js)
- [ ] No blocking JS error if animation target elements are missing.
- [ ] Count-up, reveal, ripple, modal animation still run.
- [ ] App remains usable when animations are skipped.

## Stage 7 (admin-sidebar.js rename + var->const/let) - high risk
- [ ] All renamed functions are updated in every call site.
- [ ] Sidebar account menu opens/closes as before.
- [ ] Accessibility modal still works.

## Stage 8 (billing.js)
- [ ] Billing confirmation flow still redirects and displays notification.

## Stage 9-11 (CSS refactor) - medium/high visual risk
- [ ] No typography/color regression on all key pages.
- [ ] Sidebar/topbar/cards/modals retain expected spacing and hierarchy.
- [ ] No overflow or clipping introduced.

## Stage 12 (upload.html inline JS) - high risk
- [ ] Drag-drop/file input/pasted text all function.
- [ ] Processing state and progress transitions work.
- [ ] Quiz start/render/answer/next/results works end-to-end.

## Stage 13 (module + history + results inline JS)
- [ ] Module schedule modal actions still work.
- [ ] History list filtering and summary modal still work.
- [ ] Results page still loads and retake action works.

## Stage 14 (dashboard + index inline JS)
- [ ] Dashboard greeting logic and stats render correctly.
- [ ] New redirect handler in index routes by role correctly.

## Stage 15 (billing + payment + confirm inline JS) - high risk
- [ ] Payment input formatters still enforce expected format.
- [ ] Review order and submit payment still complete.
- [ ] Confirm modal actions still map to correct handlers.

## Stage 16 (admin-users inline JS) - very high risk
- [ ] Every renamed symbol has updated call sites.
- [ ] Table actions still map to proper API endpoints.
- [ ] User detail modal tabs and edit actions remain functional.

## Stage 17 (admin-stats + admin-history inline JS)
- [ ] Chart rendering works with API data.
- [ ] History filtering/pagination/modal still work.

---

## 4) Quick Regression Commands

### Search for stale symbol names after rename stages

```powershell
Set-Location E:\AISummarize-Project\Learnova
rg "_adminCloseAccountMenu|_adminToggleAccountMenu|_adminOpenAccessibility|_adminCloseAccessibility|switchUdmTab\(|\bcap\(|openModal\(" frontend
```

Expected: no matches after relevant stage completion.

### Search for new syntax issues quickly

```powershell
Set-Location E:\AISummarize-Project\Learnova
rg "TODO_REFACTOR_CHECK|FIXME_REFACTOR" frontend
```

Expected: no leftover temporary markers.

---

## 5) Merge Gate (must pass before finishing any stage)

- [ ] Stage scope completed exactly as planned.
- [ ] Core Smoke Test Pack passed.
- [ ] Stage-Specific Gate passed.
- [ ] No new console errors.
- [ ] Commit message includes stage number and summary.

Commit example:

```text
refactor(stage-5): add jsdoc and readability improvements for system admin module
```
