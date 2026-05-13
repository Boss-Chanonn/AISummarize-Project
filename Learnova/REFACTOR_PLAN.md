# LEARNOVA FRONTEND — REFACTOR PLAN
> Senior Frontend Developer Review  
> Date: 2026-05-13  
> All stages must be approved one at a time before code is written.

---

## FILES ANALYSED

| File | Lines |
|---|---|
| js/app.js | 1851 |
| css/style.css | 1459 |
| admin-users.html | 1027 |
| upload.html | 667 |
| module.html | 351 |
| admin-history.html | 301 |
| js/animations.js | 290 |
| index.html | 287 |
| dashboard.html | 286 |
| admin-stats.html | 272 |
| billing.html | 261 |
| history.html | 215 |
| js/admin-sidebar.js | 212 |
| system-admin.html | 209 |
| payment.html | 203 |
| css/admin-users.css | 185 |
| confirm.html | 149 |
| results.html | 134 |
| js/billing.js | 94 |
| css/admin-base.css | 57 |
| css/admin-stats.css | 41 |

---

## STAGE 1 — js/app.js · Part 1 · User State, Helpers & Theme (lines 1–100)

**Issues found:**
- `LEARNOVA_USER` object has no comment explaining what it stores or where it comes from
- `getHistoryItem()`, `getRecentActivity()`, `getResumeQuizUrl()`, `escapeHtml()` — no comments on any of them
- `renderSummaryMarkup()` has 3 inline ternary one-liners with no explanation (`ctaLabel`, `ctaHandler`, `ctaHint` all set conditionally on one line each)
- `applyTheme()`, `applyFontSize()` — no comments
- `loadPrefs()` calls two functions on the same line: `applyTheme(t); applyFontSize(s);`
- `getInitials()` has a 6-step method chain on one line — hard to follow for a beginner
- No top-level section banner comments at start of file explaining what `app.js` is and how it is organised
- Section delimiters use inconsistent styles throughout the file (some use `/* ── X ── */`, Section 7 uses `/* ==== */`)

**What will be done:**
- Add file-level banner comment explaining `app.js` purpose
- Add JSDoc to all 9 functions in this section
- Break `renderSummaryMarkup` ternaries into named variables
- Break `getInitials` chain into readable named steps
- Split `loadPrefs` one-liner into two lines
- Standardise all section delimiters to the format shown in the instructions

**Functions to comment: 9**

---

## STAGE 2 — js/app.js · Part 2 · Toast, UI Sync & Sidebar Menu (lines 101–220)

**Issues found:**
- `showToast()` builds the element with chained one-liners (`t = createElement`, `t.id=`, `t.className=`, `t.innerHTML=` all on one line); `clearTimeout` on same line as `classList.add`
- `syncUserUI()` has chained `forEach` calls with no comment explaining what each block does
- `getAvatarMarkup()` — no comment
- `renderSidebarAccountMenuMarkup()` returns a large HTML string with no explanation of what sections it renders
- `closeSidebarAccountMenu()` — no comment
- `toggleSidebarAccountMenu()` — no comment; checks for `existingMenu` on same line as creating `mount` element
- `logoutUser()` — no comment; catch block is fine but `e` is unused and unexplained
- `handleSidebarAccountAction()` — no comment; four `if`-statements in a row with no explanation of what each action does

**What will be done:**
- Add JSDoc to all 8 functions in this section
- Break `showToast()` element creation into separate named lines
- Add inline comments inside `syncUserUI()` to label each block
- Add inline comments inside `toggleSidebarAccountMenu()` for each logical step
- Add `/* -- Group -- */` sub-labels to separate Toast, UI sync, and Account menu groups

**Functions to comment: 8**

---

## STAGE 3 — js/app.js · Part 3 · Settings, Profile & Sidebar HTML (lines 221–560)

**Issues found:**
- `openSettings()` has no comment; large HTML template with two inline `map()` chains (themeSwatches + planFeatures) with no explanation; each `map()` uses arrow functions with nested template literals
- `closeSettings()`, `triggerAvatarUpload()` — no comments
- `handleAvatarUpload()` — no comment; `reader.onload` uses an arrow function with no explanation
- `openEditProfile()` — no comment; complex template literal with inline ternary for `pendingEmailNotice`
- `closeEditProfile()` — one-liner, no comment
- `saveProfile()` — no comment; long chain of if conditions with no explanation of validation flow; `emailChanged` and `wantsPasswordChange` are ok names but the logic block checking all three toast variants is confusing
- `upgradeToPro()` — no comment
- `openProfile()` — no comment; inline array map building profile rows is clever but unreadable for a beginner
- `closeProfile()` — one-liner, no comment
- `renderSidebar()` — no comment; large template literal; inline ternaries for active page classes throughout

**What will be done:**
- Add JSDoc to all 10 functions
- Break `renderSidebarAccountMenuMarkup` HTML template into labeled sections with comments
- In `saveProfile()`: extract validation steps into named boolean variables with comments
- In `openProfile()`: extract the profile fields array into a named `const` with a comment
- In `openSettings()`: extract theme swatches map and plan features map into named variables

**Functions to comment: 10**

---

## STAGE 4 — js/app.js · Part 4 · History Modals (lines 561–745)

**Issues found:**
- `ensureHistoryModalMounts()` — no comment
- `openHistoryDetail()` — no comment; complex HTML template with inline SVG score ring; two chained `map()` calls for strengths/weaknesses/studyNext badges on one line each; q-list `map()` with nested ternaries all on one line
- `closeHistoryDetail()` — no comment
- `openHistorySplit()` — no comment; near-duplicate of `openHistoryDetail()` — the score ring SVG and q-list HTML are copy-pasted between these two functions (**duplicate code**)
- `closeHistorySplit()` — no comment
- `circ` / `offset` variables in both open functions have no comment explaining what they are (SVG stroke math)

**What will be done:**
- Add JSDoc to all 5 functions
- Add inline comments explaining the stroke-dashoffset calculation for the SVG score ring
- Extract the question breakdown list HTML into a helper function `renderQuestionListMarkup(questions)` to eliminate the duplicate HTML
- Break the long one-liner `map()` chains for badges into readable multi-line form

**Functions to comment: 5 (+ 1 new helper)**

---

## STAGE 5 — js/app.js · Part 5 · System Admin (lines 746–1851)

**Issues found:**
- 41 functions with zero comments
- `SYS_STATE` object has no comment explaining its fields
- `SYS_SECTIONS` object has no comment
- `isSystemAdminPage()` — no comment
- `renderSystemAdminSidebar()` — no comment; large template
- `openSysAccountMenu()` / `closeSysAccountMenu()` — no comments
- `logoutSystemAdmin()` — no comment
- `verifySysAdmin()` — no comment; critical auth function with no explanation of what it checks
- `sysAdminFetch()` — no comment; JSON parse `try/catch` with no explanation
- `sysTimedFetch()` — no comment; wraps `sysAdminFetch` but unclear why
- `switchSysSection()` — no comment
- `showSysLoading()` — no comment; 4 if-blocks with no labels
- `renderServiceStatus()` — no comment; inline string conversion logic for mongodb/ollama states
- `renderRealtimeStats()` / `renderApiHealth()` — no comments
- `loadSystemOverview()` — no comment
- `formatSysDate()` / `normalizeSysUsers()` — no comments
- `applySysUserFilters()` — no comment; uses optional chaining (`?.value`) without explanation for beginners
- `renderUserTable()` — no comment; very long HTML string concatenation per row
- `loadUserControl()` — no comment
- `openSysRoleModal()` / `closeSysRoleModal()` — no comments
- `changeSysUserRole()` — no comment
- `resetSysUserPassword()` — no comment
- `openSysDeleteModal()` / `closeSysDeleteModal()` — no comments
- `syncSysDeleteConfirmButton()` — no comment
- `deleteSysUser()` — no comment
- `formatBytes()` — no comment; complex `while` loop with no explanation
- `estimateCollectionSize()` — no comment
- `fetchSysCollectionNames()` — no comment; complex error-message parsing to extract collection names from API error
- `loadDatabase()` — no comment
- `renderCollections()` — no comment
- `expandCollection()` — no comment
- `renderCollectionDocs()` — no comment
- `updateDeleteSelectedBtn()` — no comment
- `openSysDbDeleteModal()` / `closeSysDbDeleteModal()` — no comments
- `deleteSelectedDocs()` — no comment
- `filterCollectionDocs()` — no comment
- `classifyLogType()` — no comment; pattern matching with no explanation
- `formatTimeAgo()` — no comment; diffMin/diffHr/diffDay logic
- `renderFailedLogins()` — no comment; groupBy logic with no explanation
- `filterActivityLogs()` — no comment
- `renderActivityLogs()` — no comment
- `renderAuditTrail()` — no comment; `iconByMethod` map has no comment
- `loadSecurity()` — no comment
- `exportSysLogsCsv()` — no comment; Blob/URL creation logic has no explanation for a beginner
- `bindSystemAdminEvents()` — no comment; long event delegation block
- `DOMContentLoaded` handler — no comment

**What will be done:**
- Add JSDoc to all 41 functions
- Add comments to `SYS_STATE` and `SYS_SECTIONS` objects
- Add sub-section comments separating: Overview, User Control, Database Manager, Security Center, Events
- Break `applySysUserFilters()` optional chaining into safer readable form
- Add comments to the `formatBytes` while loop
- Add comments to the `fetchSysCollectionNames` error-parsing logic
- Add comments to `renderFailedLogins` groupBy logic
- Add comments to `classifyLogType` pattern table
- Add comments to `exportSysLogsCsv` Blob/URL pattern

**Functions to comment: 41**

---

## STAGE 6 — js/animations.js

**Issues found:**
- First IIFE (page transition) has no label — unclear purpose at a glance
- Second IIFE (scroll-reveal IntersectionObserver) has no label
- `countUp()` — no comment; `ease = 1 - Math.pow(1-p, 3)` has no explanation (cubic ease-out formula)
- `initCountUp()` — no comment
- `animateHistoryItems()` — no comment
- `addRipple()` — no comment; `size = Math.max(rect.width, rect.height) * 1.25` has no explanation
- `initButtonRipple()` — no comment
- `swapPanelContent()` — no comment; multi-step animation logic with several `setTimeout` calls and no labels
- `revealSequence()` — no comment
- `setModalSourceFromEvent()` — no comment; complex `closest()` chain has no explanation
- `animateModalFromSource()` — no comment; scaleX/scaleY transformation math has no explanation
- `initTilt()` — no comment; mousemove formula has no explanation
- `animateScoreRing()` — no comment; `circ = 251.2` magic number (2πr where r=40) has no explanation
- `animateProgressBars()` — no comment
- `animateSidebarActive()` — no comment
- `initInputGlow()` — no comment

**What will be done:**
- Add section comment labels to the two IIFEs
- Add JSDoc to all 14 named functions
- Add comments explaining the ease-out cubic formula in `countUp`
- Add a comment explaining `circ = 251.2` (the SVG circle circumference calculation 2πr)
- Add comments to the transformation math in `animateModalFromSource`
- Add `/* -- Group -- */` separators for: Page Transition, Scroll Reveal, Count-Up, History Animations, Ripple, Panel Swap, Modal Animation, Tilt Effect, Score Ring, Progress, Input Effects

**Functions to comment: 14**

---

## STAGE 7 — js/admin-sidebar.js

**Issues found:**
- Uses `var` throughout — inconsistent with `app.js` which uses `const`/`let`
- `_adminCloseAccountMenu()` and `_adminToggleAccountMenu()` use underscore-prefix naming — inconsistent with the rest of the project which uses camelCase
- `_adminOpenAccessibility()` and `_adminCloseAccessibility()` — same issue
- No comments on any of the 7 functions
- `_adminOpenAccessibility()` builds HTML using string concatenation instead of template literals — extremely hard to read; the inline onclick strings are complex and unreadable
- The `DOMContentLoaded` handler builds sidebar HTML using string concatenation
- Short variable name `w` in: `name.split(' ').map(function(w){ return w[0]; })`

**What will be done:**
- Add JSDoc to all 7 functions
- Rename:
  - `_adminCloseAccountMenu` → `closeAdminAccountMenu`
  - `_adminToggleAccountMenu` → `toggleAdminAccountMenu`
  - `_adminOpenAccessibility` → `openAdminAccessibility`
  - `_adminCloseAccessibility` → `closeAdminAccessibility`
- Change `var` → `const` / `let` throughout
- In `_adminOpenAccessibility`: break the long inline onclick into a named step with a comment
- Rename `w` → `word` in the initials split map
- Add `/* -- Group -- */` section comments

**Functions to comment: 7**

---

## STAGE 8 — js/billing.js

**Issues found:**
- `getBillingStatus()` — already has JSDoc (good), but the catch block silently discards `e` — worth a comment
- `confirmPayment()` — already has JSDoc (good)
- `showSuccessNotification()` — has a comment, but the `notification.style.cssText` is a very long inline style string with no explanatory comments on individual styles; the animation injection check pattern is unclear for a beginner

**What will be done:**
- Keep existing JSDoc (it is correct and helpful)
- Add inline comments to `showSuccessNotification()` breaking down the style string into labeled groups (layout, appearance, animation)
- Add a comment explaining the style injection pattern (why it checks for existing style element)
- Add file-level section comments

**Functions to comment: 3 (already commented, improvements only)**

---

## STAGE 9 — css/style.css · Part 1 (Sections 1–4)

**Issues found:**
- Section 1 (CSS Variables): Every variable theme block has all vars compressed 2–3 per line — hard to read or find a specific variable
- Reset rule: `*,*::before,*::after{...}` all on one line
- `html`, `body`, `a`, `button` rules all combined on one long line
- Section 3 (Sidebar): Many rules combined on single lines
- Section 4: Badge classes all on one line each; fade-up delay classes all on one line
- Many component groups inside sections 3 and 4 have no `/* -- Component Name -- */` sub-header comments
- Theme overrides (`[data-theme="light"]`, etc.) have no comment explaining they live together for maintenance

**What will be done:**
- Add `/* -- Component Name -- */` sub-headers inside each section for: Reset, Base HTML, Scrollbar, Layout, Sidebar, Nav, Tier Badges, Account Menu, Buttons, Cards, Badges, Progress, Inputs, Modals, Toast, Animations, Settings Tabs, Theme Grid, Plan Panel, History Items, Summary Blocks, Modals
- Add a comment above the theme override block
- Expand font-size delay rules (`.fade-up-1` through `.fade-up-5`) onto separate lines

**Components / sub-groups to comment: ~22**

---

## STAGE 10 — css/style.css · Part 2 (Animation System & Landing Page)

**Issues found:**
- The "PREMIUM ANIMATION SYSTEM" section has a banner comment but no sub-group comments for the individual animation families
- `.card-lift`, `.reveal`, `.panel-stage`, `.is-active`, `.ui-ripple` classes have no explanation of what component uses them
- Landing page styles (after media queries) have no section header of their own
- Many landing component groups (`.hero`, `.feature-strip`, `.pricing-section`, etc.) have no `/* -- X -- */` sub-headers
- Several CSS blocks have magic values with no comment (e.g., `stroke-dasharray` circumference in the score ring)

**What will be done:**
- Add numbered `/* -- X -- */` sub-headers throughout the animation system section
- Add section comment before the landing page styles
- Add `/* -- X -- */` sub-headers for every landing component group
- Add a comment on the SVG score ring circumference value
- Add comments to media query blocks explaining breakpoints

**Components / sub-groups to comment: ~18**

---

## STAGE 11 — css/admin-base.css + admin-stats.css + admin-users.css

**Issues found:**

*admin-base.css:*
- Has one comment at top; all rules below are compressed single-line blocks
- No section separators between: Reset, CSS Variables, Base HTML, Sidebar, Topbar, Buttons, Toast

*admin-stats.css:*
- Has minimal comments; all rules compressed on single lines
- Groups: Main Layout, Content, Cards Grid, Charts Grid, Skeleton, Error State — none have section comments

*admin-users.css:*
- 185 lines with almost no section comments
- Complex table, modal, bulk action bar, and pagination styles all without `/* -- X -- */` labels

**What will be done:**
- Add `/* -- Section Name -- */` comments to all groups in all three CSS files
- Expand the most compressed multi-property single-line rules into readable multi-line format where needed

**Sections to comment: ~18 across 3 files**

---

## STAGE 12 — upload.html · Inline JavaScript (33 functions)

**Issues found:**
- `isPro()` — one-liner with no comment
- `updateUploadUI()` — no comment; complex show/hide logic
- `triggerFileInput()` — one-liner, no comment
- `handleDrag(e, entering)` — complex one-liner, no comment
- `handleDrop(e)` — no comment
- `handleFileInput(files)` — no comment; file type filter logic is a complex one-liner using chained `filter + pop + toLowerCase`
- `renderFileList()` — no comment
- `removeFile(i)` — no comment
- `checkContent()` — no comment; complex condition on single line
- `getActiveUploadLabel()` — no comment
- `hasPastedText()` — no comment
- `isTextOnlyUpload()` — no comment
- `formatChars(count)` — no comment; complex number formatter
- `getProcessedTime()` — no comment
- `buildPastedSummary(pasted)` — no comment; very long function building a large HTML string
- `buildUploadedFileSummary()` — no comment; very long
- `buildCurrentDocument()` — no comment
- `renderDocumentInfo()` — no comment
- `setSummaryMode(active)` — no comment
- `syncCompactFile()` — no comment
- `setUploadCollapsed(collapsed)` — no comment
- `processDocument()` — no comment; long async function with FormData build, fetch, error handling, quiz setup — all without section comments inside
- `showProcessingState()` — no comment
- `updateProcessingState(progress, activeIndex)` — no comment
- `showSummary(data)` — no comment
- `startQuiz()` — no comment
- `renderQuestion(direction)` — no comment; complex panel swap call
- `selectAnswer(i)` — no comment; complex logic with disabled state
- `skipQuestion()` — complex one-liner, no comment
- `nextQuestion()` — no comment
- `showQuizResults()` — no comment; very long async function
- `resetUpload()` — no comment
- `loadResumedQuizFlow()` — no comment; complex async function

**What will be done:**
- Add JSDoc to all 33 functions
- Break `handleFileInput` filter one-liner into readable form
- Break `handleDrag` one-liner into two lines
- Break `skipQuestion` into readable multi-line
- Add section comments inside `processDocument()` and `showQuizResults()` to label each logical phase
- Add `/* ── Section ── */` comments grouping functions by responsibility: Upload UI, File Handling, Document Processing, Quiz Engine, Results

**Functions to comment: 33**

---

## STAGE 13 — module.html + history.html + results.html · Inline JS

**Issues found:**

*module.html (10 functions):*
- `openCalModal()` — no comment; 4 parameters with no explanation
- `renderCalOpts()` — no comment
- `selectCal(i)` — no comment; unclear what `i` represents
- `closeCalModal()` — no comment
- `closeOnBackdrop(e)` — no comment
- `confirmSchedule()` — no comment; long async function with no internal section comments
- `buildResCard(res)` — no comment; long HTML builder
- `loadModule()` — no comment; very long async function
- `buildResCardReal(res)` — near-duplicate of `buildResCard()` — both build a resource card; the difference is one uses static mock data and the other uses live API data. They are intentional — will be explained with comments, NOT merged.
- `showEmptyModule()` — no comment

*history.html (7 functions):*
- `fmtHistoryMeta(h)` — unclear name; no comment → rename to `formatHistoryItemMeta(item)`
- `flatAnalysis(h)` — unclear name; no comment → rename to `extractAnalysisData(historyItem)`
- `renderHistory()` — no comment; very long async function with complex template literal
- `toggleItem(id)` — no comment
- `confirmDelete(id)` — no comment
- `openSummaryModal(id)` — no comment
- `closeSummaryModal()` — no comment

*results.html (3 functions):*
- `loadResults()` — no comment; long async function with no internal section comments
- Anonymous function on `btn-retake.onclick` — no comment
- Anonymous `setTimeout` function — no comment

**What will be done:**
- Add JSDoc to all 20 functions
- Rename `fmtHistoryMeta` → `formatHistoryItemMeta`
- Rename `flatAnalysis` → `extractAnalysisData`
- Rename `selectCal(i)` param → `selectCal(calendarIndex)`
- Add a comment in `module.html` explaining the difference between `buildResCard` (placeholder) and `buildResCardReal` (live data)
- Add section comments inside `renderHistory()`, `loadModule()`, `loadResults()` to label each logical phase

**Functions to comment: 20**

---

## STAGE 14 — dashboard.html + index.html · Inline JS

**Issues found:**

*dashboard.html:*
- Auth guard IIFE — no comment explaining what it does
- `loadDashboard()` — no comment; mixes profile loading, greeting logic, stat animation, and stat subtitles without internal section labels
- `fmtMeta(item)` — unclear name; no comment → rename to `formatDocumentMeta(doc)`
- Recent activity rendering uses an anonymous function inside a data map — no comment
- Greeting logic: `h<12 / h<17` ternary one-liner

*index.html:*
- "Go to dashboard" button has a 9-line anonymous IIFE inline in its `onclick` attribute — extremely hard to read and impossible to test
- `openModal()` defined inline in index.html's script block but not commented
- Login/register HTML template strings (`loginHTML`, `registerHTML`) are very large inline variables

**What will be done:**
- Add JSDoc to `loadDashboard()`, rename `fmtMeta` → `formatDocumentMeta`
- Add inline comments to `loadDashboard()` for each phase (fetch profile, set greeting, update stats, render activity)
- Break the greeting ternary into a named variable with a comment: `getGreetingPrefix(hour)`
- In `index.html`: extract the "Go to dashboard" onclick IIFE into a named function `handleDashboardRedirect()` with a comment
- Add comments to `openModal()` and to the `loginHTML` / `registerHTML` template variables

**Functions to comment: 8**

---

## STAGE 15 — billing.html + payment.html + confirm.html · Inline JS

**Issues found:**

*billing.html (10 functions):*
- Auth guard IIFE — no comment
- `showConfirm({title, body, confirmLabel, confirmClass, onConfirm})` — no comment; destructured object parameter is confusing for a beginner
- `closeConfirm()` — no comment
- `goToPayment(planType)` — no comment
- `confirmDowngradeToFree()` — no comment
- `confirmCancelPlan(planLabel)` — no comment
- `confirmSwitchPlan(fromLabel, toLabel, toPlanType)` — no comment; 3 parameters with no explanation
- `executeDowngrade()` — no comment; long async function
- `renderBilling()` — no comment; very long async function
- `proCardHtml(planType)` — nested function with no comment

*payment.html (7 functions):*
- Auth guard IIFE — no comment
- Plan check IIFE — no comment
- `card-number` input event listener — anonymous, no comment; complex regex formatting logic
- `card-expiry` input event listener — anonymous, no comment
- `card-cvv` input event listener — anonymous, no comment
- `showError(fieldId, errorId, show)` — no comment
- `reviewOrder()` — no comment; handles validation + localStorage + redirect

*confirm.html (3 functions):*
- Auth guard IIFE — no comment
- Order review IIFE — no comment
- `submitPayment()` — no comment; long async function with payment data construction and API call

**What will be done:**
- Add JSDoc to all 20 functions
- Add comments explaining anonymous event listener callbacks
- Add section comments inside `executeDowngrade()`, `renderBilling()`, `submitPayment()` to label phases
- Add a comment explaining the destructured parameter of `showConfirm()`
- Rename the card input event anonymous handlers to named functions: `handleCardNumberInput()`, `handleExpiryInput()`, `handleCvvInput()`

**Functions to comment: 20**

---

## STAGE 16 — admin-users.html · Inline JavaScript (35+ functions)

**Issues found:**
- `fetchUsers(page)` — no comment
- `fetchStats()` — no comment
- `renderStats()` — no comment
- `applyFilters()` — no comment
- `sortBy(col)` — no comment
- `applySort()` — no comment
- `renderTable()` — no comment; very long function with complex multi-column HTML building
- `renderPagination()` — no comment
- `toggleRow(cb, id)` — no comment
- `toggleAll(masterCb)` — no comment
- `updateSelectAll()` — no comment
- `updateBulkBar()` — no comment
- `clearSelection()` — no comment
- `openModal(action, userId, userName)` — no comment; handles multiple actions (delete, role, reset, suspend, activate) → rename to `openActionModal`
- `bulkAction(action)` — no comment
- `checkConfirm()` — no comment
- `closeModal()` — no comment
- `executeAction()` — no comment; very long; handles 5+ different action types in one function
- `exportCSV()` — no comment
- `showToast(msg, type)` — **local duplicate** of `app.js` `showToast` — add comment explaining why it exists locally (admin pages do not load `app.js`)
- `escHtml(s)` — **local duplicate** of `escapeHtml()` from `app.js` — add comment explaining why it is local
- `escAttr(s)` — no comment
- `formatDateDisplay(dateStr)` — no comment
- `switchUdmTab(n)` — no comment; unclear what `UDM` stands for → rename to `switchUserDetailTab(tabNumber)`
- `openUserModal(userId)` — no comment; long function
- `closeUserModal()` — no comment
- `startProfileEdit()` — no comment
- `cancelProfileEdit()` — no comment
- `saveProfile()` — no comment; long async function
- `cap(s)` — cryptic name, no comment → rename to `capitalizeFirst(str)`
- `startAccountEdit(field)` — no comment
- + ~5 more functions (cancelAccountEdit, saveAccountField, openDeleteModal, etc.)

**What will be done:**
- Add JSDoc to all 35+ functions
- Rename `openModal` → `openActionModal`
- Rename `switchUdmTab` → `switchUserDetailTab`
- Rename `cap` → `capitalizeFirst`
- Add comment to `escHtml` and `showToast` explaining why they are local duplicates
- Add section comments grouping: Data Loading, Filtering & Sorting, Table Rendering, Row Selection, Bulk Actions, Modals, User Detail Modal, Helpers

**Functions to comment: 35+**

---

## STAGE 17 — admin-stats.html + admin-history.html · Inline JS

**Issues found:**

*admin-stats.html (6 functions):*
- `renderCards(s)` — no comment; builds 3 stat cards from API data; uses dense template literal
- `renderLineChart(data)` — no comment; builds SVG path using complex math (normalisation, polyline points) with no explanation
- `renderBarChart(data)` — no comment; similar SVG math
- `loadStats()` — no comment; long async function
- `revalidateRole()` — no comment; important auth function
- `showToast(msg, type)` — local duplicate (same as Stage 16)

*admin-history.html (10 functions):*
- `fetchHistory(page)` — no comment
- `applyFilter()` — no comment
- `renderList()` — no comment; long template builder
- `getSummarySnippet(h)` — no comment; truncates summary body text
- `toggleItem(id)` — no comment
- `renderPagination()` — no comment
- `openSumModal(id)` — no comment
- `closeSumModal()` — no comment
- `showToast(msg, type)` — local duplicate
- `escHtml(s)` — local duplicate

**What will be done:**
- Add JSDoc to all 16 functions
- Add comments to SVG path math in `renderLineChart()` and `renderBarChart()` explaining normalisation formula
- Add section comments grouping functions in each file
- Add comments to local `showToast` and `escHtml` explaining why they are local

**Functions to comment: 16**

---

## SUMMARY

| # | Stage | Target | Functions |
|---|---|---|---|
| 1 | js/app.js — User State, Helpers, Theme | app.js lines 1–100 | 9 |
| 2 | js/app.js — Toast, UI Sync, Sidebar Menu | app.js lines 101–220 | 8 |
| 3 | js/app.js — Settings, Profile, Sidebar HTML | app.js lines 221–560 | 10 |
| 4 | js/app.js — History Modals | app.js lines 561–745 | 5 (+1 new helper) |
| 5 | js/app.js — System Admin | app.js lines 746–1851 | 41 |
| 6 | js/animations.js | full file | 14 |
| 7 | js/admin-sidebar.js | full file | 7 |
| 8 | js/billing.js | full file | 3 |
| 9 | css/style.css — Variables through Components | style.css lines 1–~600 | ~22 groups |
| 10 | css/style.css — Animation System + Landing | style.css lines ~600–end | ~18 groups |
| 11 | css/admin-base + admin-stats + admin-users | 3 CSS files | ~18 groups |
| 12 | upload.html inline JS | upload.html | 33 |
| 13 | module + history + results inline JS | 3 HTML files | 20 |
| 14 | dashboard + index inline JS | 2 HTML files | 8 |
| 15 | billing + payment + confirm inline JS | 3 HTML files | 20 |
| 16 | admin-users.html inline JS | admin-users.html | 35+ |
| 17 | admin-stats + admin-history inline JS | 2 HTML files | 16 |
| | | **TOTAL** | **~235** |

### Duplicate code found
| Location | Description |
|---|---|
| `openHistoryDetail()` + `openHistorySplit()` in app.js | Question breakdown list HTML is copy-pasted — will be extracted to a helper |
| `escHtml()` in admin-users.html, admin-history.html | Local duplicates — intentional, will be explained with comments |
| `showToast()` in admin-users.html, admin-stats.html, admin-history.html | Local duplicates — intentional, will be explained with comments |

### Naming improvements
| Current | Improved | File |
|---|---|---|
| `fmtMeta` | `formatDocumentMeta` | dashboard.html |
| `fmtHistoryMeta` | `formatHistoryItemMeta` | history.html |
| `flatAnalysis` | `extractAnalysisData` | history.html |
| `selectCal(i)` | `selectCal(calendarIndex)` | module.html |
| `switchUdmTab` | `switchUserDetailTab` | admin-users.html |
| `cap` | `capitalizeFirst` | admin-users.html |
| `openModal` | `openActionModal` | admin-users.html |
| `_adminCloseAccountMenu` | `closeAdminAccountMenu` | admin-sidebar.js |
| `_adminToggleAccountMenu` | `toggleAdminAccountMenu` | admin-sidebar.js |
| `_adminOpenAccessibility` | `openAdminAccessibility` | admin-sidebar.js |
| `_adminCloseAccessibility` | `closeAdminAccessibility` | admin-sidebar.js |

---

*To begin: say **"start stage 1"***
