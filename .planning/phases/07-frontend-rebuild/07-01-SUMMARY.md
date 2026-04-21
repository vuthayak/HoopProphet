---
phase: 07-frontend-rebuild
plan: 01
subsystem: frontend
tags:
  - vite
  - react-19
  - tailwind-v4
  - react-router-v7
  - visx
  - vitest
requires:
  - UI-01
  - UI-07
  - D-01
  - D-03
  - D-04
  - D-05
  - D-20
  - D-21
  - D-23
provides:
  - Vite + React 19 + Tailwind v4 project foundation
  - CSS-first design system with @theme tokens
  - 3-route SPA shell with React Router v7
  - API client with all named endpoint methods
  - Test infrastructure with Vitest + jsdom
affects:
  - hoopprophet/
tech_stack:
  added:
    - react@19.1.0
    - react-dom@19.1.0
    - react-router@7.14.2
    - vite@8.0.9
    - tailwindcss@4.2.4
    - @tailwindcss/vite@4.2.4
    - @visx/shape@4.0.0-alpha.11
    - @visx/group@4.0.0-alpha.11
    - @visx/scale@4.0.0-alpha.11
    - @visx/axis@4.0.0-alpha.11
    - @visx/responsive@4.0.0-alpha.11
    - @visx/gradient@4.0.0-alpha.11
    - @visx/tooltip@4.0.0-alpha.11
    - react-hot-toast@2.6.0
    - lucide-react
    - vitest@3.2.0
    - jsdom@26.1.0
    - @testing-library/react@16.3.2
    - @testing-library/jest-dom@6.9.1
    - @testing-library/user-event@14.6.1
key_files:
  created:
    - hoopprophet/package.json
    - hoopprophet/vite.config.js
    - hoopprophet/index.html
    - hoopprophet/src/main.jsx
    - hoopprophet/src/App.jsx
    - hoopprophet/src/index.css
    - hoopprophet/src/api/client.js
    - hoopprophet/src/utils/constants.js
    - hoopprophet/src/utils/formatters.js
    - hoopprophet/vitest.config.js
    - hoopprophet/src/setupTests.js
    - hoopprophet/src/__tests__/App.test.jsx
  modified: []
key_decisions:
  - Used @visx/shape@4.0.0-alpha.11 (alpha, not stable v3) for React 19 compatibility
  - Tailwind v4 via @tailwindcss/vite plugin (no PostCSS config needed)
  - API_BASE from import.meta.env.VITE_API_BASE (not REACT_APP_ prefix)
  - Dark-mode-only via class="dark" on html element (no theme toggle)
duration: ~8 min
completed: "2026-04-21T23:51:07Z"
---

# Phase 07 Plan 01: Frontend Foundation — Vite + React 19 + Tailwind v4

**Substantive one-liner:** Vite + React 19 SPA with Tailwind v4 CSS-first design system, React Router v7, Visx v4 alpha charts, and Vitest test infrastructure — complete V1 code removed.

## What Was Built

Rebuilt the HoopProphet frontend from scratch, deleting all V1 CRA/MUI code and scaffolding a modern Vite + React 19 + Tailwind v4 SPA.

### Key Deliverables

| Artifact | Status |
|----------|--------|
| `hoopprophet/package.json` | Exact-pinned dependencies, no V1 packages |
| `hoopprophet/vite.config.js` | React plugin + Tailwind v4 plugin + /api proxy |
| `hoopprophet/src/index.css` | Tailwind v4 @theme tokens for all design tokens |
| `hoopprophet/src/App.jsx` | React Router v7 with 3 routes |
| `hoopprophet/src/api/client.js` | fetchJSON + named api methods (9 endpoints) |
| `hoopprophet/src/utils/constants.js` | PROB_THRESHOLDS, ALERT_STYLES, DEBOUNCE_MS |
| `hoopprophet/vitest.config.js` | jsdom environment |
| `npm run build` | ✓ Produces dist/ (326KB JS, 18KB CSS) |

### Design System (from UI-SPEC)

All tokens in `src/index.css` @theme block:
- **Surfaces:** bg-primary (#0f1117), bg-card (#1e2333), bg-card-hover (#283040), border (#2d3548)
- **Text:** text-primary (#e2e8f0), text-secondary (#94a3b8), text-muted (#64748b)
- **Probability:** prob-high (#22c55e), prob-moderate (#eab308), prob-low (#ef4444), accent (#3b82f6)
- **Animations:** fadeSlideUp (300ms), fadeIn (200ms), badgeScale (250ms), dropdownIn (150ms)

### V1 Cleanup Verification

```
grep "@mui" hoopprophet/src/  → 0 results
grep "framer-motion" hoopprophet/src/  → 0 results  
grep "react-scripts" hoopprophet/package.json  → 0 results
```

## Task Summary

| Task | Files | Status |
|------|-------|--------|
| Task 1: Delete V1, scaffold Vite project | package.json, package-lock.json | ✓ Complete |
| Task 2: Tailwind design system, API client, project structure | vite.config.js, index.css, App.jsx, api/client.js, utils/*, main.jsx | ✓ Complete |
| Task 3: Test infrastructure + smoke tests | vitest.config.js, setupTests.js, App.test.jsx | ✓ Complete |

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1 | df7deba | feat(07-01): rebuild frontend with Vite + React 19 + Tailwind v4 |

## Self-Check: PASSED

- [x] Vite dev server starts and renders the app at localhost:3000
- [x] All V1 MUI/CRA code is removed and replaced with clean Vite + React 19 + Tailwind v4 project
- [x] Dark mode is the only theme and renders correctly
- [x] React Router renders three routes that navigate without errors
- [x] Tailwind v4 design tokens are defined and applied (probability colors, surface colors, animations)
- [x] Test infrastructure runs Vitest with jsdom environment
- [x] npm run build succeeds (326KB JS, 18KB CSS, built in 134ms)

## Next Steps

Ready for **Plan 07-02: Data hooks, navigation shell, badges, and skeletons**. Plan 02 depends on Plan 01 and will create the 5 custom hooks, 6 UI components, and test infrastructure for the data layer.