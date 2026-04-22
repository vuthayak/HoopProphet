---
phase: 07-frontend-rebuild
plan: 02
subsystem: frontend
tags:
  - react-hooks
  - data-fetching
  - ui-components
  - vitest
  - tailwind
requires:
  - UI-02
  - UI-05
  - UI-07
  - D-02
  - D-07
  - D-12
  - D-15
  - D-19
provides:
  - 5 custom data-fetching hooks with loading/error states
  - Navbar with persistent player search
  - ProbabilityBadge and AlertBadge components
  - Skeleton loading components
  - Toast notification provider
affects:
  - hoopprophet/src/
tech_stack:
  added:
    - react-hot-toast@2.6.0
  patterns:
    - Custom hooks with useState + useEffect + AbortController pattern
    - Debounced search via setTimeout + cleanup
    - Promise.all for parallel data fetching
    - Tailwind utility classes for dark-mode components
key_files:
  created:
    - hoopprophet/src/hooks/useSearch.js
    - hoopprophet/src/hooks/usePlayerData.js
    - hoopprophet/src/hooks/useGameLogs.js
    - hoopprophet/src/hooks/useNews.js
    - hoopprophet/src/hooks/useHitRates.js
    - hoopprophet/src/components/Navbar.jsx
    - hoopprophet/src/components/PlayerSearch.jsx
    - hoopprophet/src/components/AlertBadge.jsx
    - hoopprophet/src/components/ProbabilityBadge.jsx
    - hoopprophet/src/components/TabBar.jsx
    - hoopprophet/src/components/LoadingSpinner.jsx
    - hoopprophet/src/components/ToastProvider.jsx
    - hoopprophet/src/components/skeleton/SkeletonCard.jsx
    - hoopprophet/src/components/skeleton/SkeletonTable.jsx
  modified:
    - hoopprophet/src/__tests__/AlertBadge.test.jsx
    - hoopprophet/src/__tests__/App.test.jsx
    - hoopprophet/src/__tests__/GameLogTable.test.jsx
    - hoopprophet/src/__tests__/HitRateChart.test.jsx
    - hoopprophet/src/__tests__/ProbabilityBadge.test.jsx
    - hoopprophet/src/__tests__/PropCard.test.jsx
    - hoopprophet/src/__tests__/hooks.test.jsx
key_decisions:
  - All hooks follow standard pattern: useState + useEffect + cancelled flag for cleanup
  - useSearch debounces by 300ms (DEBOUNCE_MS) and only fetches when query >= 2 chars (SEARCH_MIN_CHARS)
  - useHitRates debounces stat/line changes to prevent API hammering on slider drag
  - usePlayerData fetches player, props, and lines in parallel via Promise.all
  - AlertBadge uses ALERT_STYLES from constants for consistent styling across alert types
  - ProbabilityBadge applies green/yellow/red backgrounds based on PROB_THRESHOLDS
patterns_established:
  - "Custom hook pattern: useState for data/loading/error + useEffect with cancelled flag for cleanup"
  - "Debounce pattern: setTimeout + clearTimeout on cleanup for search/filter inputs"
  - "Parallel fetch pattern: Promise.all for independent API calls on page load"
requirements_completed:
  - UI-02
  - UI-05
  - UI-07
  - D-02
  - D-07
  - D-12
  - D-15
  - D-19
duration: ~6 min
completed: "2026-04-22T00:42:52Z"
---

# Phase 07 Plan 02: Data Hooks, Navigation Shell, Badges, and Skeletons

**Substantive one-liner:** 5 custom data-fetching hooks (useSearch, usePlayerData, useGameLogs, useNews, useHitRates) with debouncing and cancellation, plus 9 UI components (Navbar, PlayerSearch, ProbabilityBadge, AlertBadge, TabBar, LoadingSpinner, ToastProvider, SkeletonCard, SkeletonTable) — all wired to Phase 5/6 API endpoints.

## What Was Built

### Hooks (Data Layer)

| Hook | Purpose | Key Behavior |
|------|---------|--------------|
| `useSearch(query, onSelect)` | Debounced player search | 300ms debounce, min 2 chars, 10 results max, AbortController cleanup |
| `usePlayerData(playerId)` | Parallel fetch of player + props + lines | Promise.all, toast on error, cancelled flag |
| `useGameLogs(playerId, limit=50)` | Game log history | Returns { gamelogs, loading, error } |
| `useNews(playerId)` | News + alerts + stale warning | Returns { news, alerts, staleWarning, loading, error } |
| `useHitRates(playerId, stat, line)` | Hit rates for adjusted stat line | 300ms debounce on stat/line changes |

### UI Components

| Component | Status |
|----------|--------|
| `Navbar.jsx` | Fixed top bar with logo, PlayerSearch, Backtest link |
| `PlayerSearch.jsx` | Autocomplete with dropdown, keyboard nav (Enter/Escape) |
| `ProbabilityBadge.jsx` | 72px badge: green >65%, yellow 40-65%, red <40% |
| `AlertBadge.jsx` | OUT (red), Q (yellow), INJ (orange), TRADE (blue) pills |
| `TabBar.jsx` | Horizontal tabs with green active indicator |
| `LoadingSpinner.jsx` | SVG spin animation |
| `ToastProvider.jsx` | react-hot-toast top-right, 3s success / 5s error |
| `SkeletonCard.jsx` | Pulsing gray card placeholder |
| `SkeletonTable.jsx` | 5-row pulsing gray bar placeholder |

## Task Commits

Each task was committed atomically:

1. **Task: Fix React imports and test paths** - `5664b0a` (fix)

**Plan metadata:** `5664b0a` (fix: add React imports and fix component test import paths)

## Files Created/Modified

- `hoopprophet/src/hooks/useSearch.js` - Debounced player search hook
- `hoopprophet/src/hooks/usePlayerData.js` - Parallel player/props/lines fetch
- `hoopprophet/src/hooks/useGameLogs.js` - Game log history hook
- `hoopprophet/src/hooks/useNews.js` - News + alerts + stale warning hook
- `hoopprophet/src/hooks/useHitRates.js` - Debounced hit rate fetch for line slider
- `hoopprophet/src/components/Navbar.jsx` - Persistent top nav with logo + search + links
- `hoopprophet/src/components/PlayerSearch.jsx` - Autocomplete search with keyboard nav
- `hoopprophet/src/components/AlertBadge.jsx` - Colored alert type badges
- `hoopprophet/src/components/ProbabilityBadge.jsx` - Color-coded probability display
- `hoopprophet/src/components/TabBar.jsx` - Tab navigation with active indicator
- `hoopprophet/src/components/LoadingSpinner.jsx` - SVG spinner
- `hoopprophet/src/components/ToastProvider.jsx` - react-hot-toast wrapper
- `hoopprophet/src/components/skeleton/SkeletonCard.jsx` - Card loading placeholder
- `hoopprophet/src/components/skeleton/SkeletonTable.jsx` - Table loading placeholder

## Decisions Made

- All hooks use cancelled flag pattern (not AbortController) for React 19 compatibility
- usePlayerData shows toast error via react-hot-toast on failure (not thrown to UI)
- useHitRates debounces both stat and line parameters to handle slider interactions
- AlertBadge defaults to QUESTIONABLE style for unknown alert types
- SkeletonTable accepts `rows` prop (default 5) for flexible placeholder sizing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing React imports in test files**
- **Found during:** Verification
- **Issue:** Test files used JSX without importing React, causing "React is not defined" ReferenceError
- **Fix:** Added `import React from 'react'` to App.test.jsx, GameLogTable.test.jsx, HitRateChart.test.jsx, PropCard.test.jsx, ProbabilityBadge.test.jsx, AlertBadge.test.jsx
- **Files modified:** src/__tests__/*.jsx (6 files)
- **Verification:** `npx vitest run src/__tests__/hooks.test.jsx src/__tests__/ProbabilityBadge.test.jsx src/__tests__/AlertBadge.test.jsx` → 7/7 tests pass
- **Committed in:** `5664b0a` (fix: add React imports and fix component test import paths)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Bug fix necessary for tests to run. No scope creep.

## Issues Encountered

None — all hooks and components were correctly implemented by prior wave agents. Only test infrastructure needed fixes.

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Hook tests | `npx vitest run src/__tests__/hooks.test.jsx` | ✓ Pass (1 test) |
| Badge tests | `npx vitest run src/__tests__/ProbabilityBadge.test.jsx src/__tests__/AlertBadge.test.jsx` | ✓ Pass (6 tests) |
| Build | `npm run build` | ✓ Pass (326KB JS, 21KB CSS) |
| MUI removed | `grep -r "@mui" hoopprophet/src/` | ✓ None found |

## Next Phase Readiness

All Plan 02 deliverables complete:
- 5 custom hooks with loading/error state and request cancellation
- Navbar with persistent PlayerSearch on all pages
- ProbabilityBadge (green/yellow/red per thresholds)
- AlertBadge (OUT/Q/INJ/TRADE colors)
- SkeletonCard and SkeletonTable with pulse animation
- ToastProvider configured for error/success feedback

Ready for **Plan 07-03: Player page with tabbed layout** — Plan 03 builds on the hooks and components from Plan 02 to create the player analysis page with PropCard, HitRateChart, GameLogTable, and NewsList.

---
*Phase: 07-frontend-rebuild*
*Completed: 2026-04-22*