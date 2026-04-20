# Learnova — AI Learning Platform (Frontend Prototype)

A dark, minimal, premium-feeling frontend prototype for the CS301 Investigative Studio project.

## How to open

Simply double-click any `.html` file to open it in your browser.
**No server or installation required.**

Recommended entry point: `landing.html`

## Pages

| File | Description |
|------|-------------|
| `landing.html` | Public landing page with sign in / register modal |
| `index.html` | Dashboard — stats, quick actions, recent activity |
| `upload.html` | Upload document + AI summary (interactive) |
| `results.html` | Quiz results, strengths/weaknesses, feedback |
| `module.html` | Learning module with resources + calendar scheduling |

## Navigation

All pages are linked together via the sidebar and buttons.
The sidebar appears on all authenticated pages (dashboard, upload, results, module).

## Interactive features

- **upload.html** — Drop a file or paste text, click "Summarise with AI" to see the loading state then the summary panel appear
- **module.html** — Click "Schedule" on any resource card to open the calendar modal, pick a calendar, and confirm. The card updates to "Scheduled" and the progress bar ticks up
- **landing.html** — Click "Sign in" or "Get started" to open the auth modal

## File structure

```
learnova/
├── landing.html        ← Start here
├── index.html          ← Dashboard
├── upload.html         ← Upload & summarise
├── results.html        ← Quiz results
├── module.html         ← Learning module
├── css/
│   └── style.css       ← Shared design system
├── js/
│   └── app.js          ← Shared JS (nav, toast, sidebar)
└── README.md
```

## Design notes

- Font: DM Serif Display (headings) + DM Sans (body) via Google Fonts
- Colour palette: `#0A0A0A` base, `#F0EDE8` cream, `#C8B89A` gold accent
- Requires an internet connection to load Google Fonts (fallback: system sans-serif)
