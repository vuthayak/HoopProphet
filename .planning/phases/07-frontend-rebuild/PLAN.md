---
phase: 07-frontend-rebuild
created: 2026-04-21
plans: 4
status: ready
---

# Phase 7: Frontend Rebuild — Plan Overview

## Goal

Component-based React app with player analysis, back-test display, and hit rate visualization — replacing V1's monolithic 590-line App.js with a clean, modern SPA built on Vite, React 19, Tailwind CSS v4, React Router, and Visx charts.

## Requirements Covered

| Requirement | Description | Plan |
|-------------|-------------|------|
| UI-01 | Component-based architecture | 01 (project scaffold, folder structure) |
| UI-02 | Autocomplete player search | 02 (PlayerSearch, useSearch) |
| UI-03 | Prop cards with hit rate charts, ML probability, adjustable lines | 03 (PropCard, HitRateChart, LineSlider) |
| UI-04 | Game log table | 03 (GameLogTable) |
| UI-05 | News/injury flags on player page | 02 (AlertBadge), 03 (NewsList) |
| UI-06 | Back-test page showing model accuracy and calibration | 04 (BacktestPage, CalibrationChart) |
| UI-07 | Clean, modern, data-focused dashboard design | 01 (Tailwind design system), all plans |
| UI-08 | Bar charts for hit rates across L5/L10/L20/season windows | 03 (HitRateChart with Visx) |
| PROP-02 | Default stat lines from player performance | 02 (usePlayerData), 03 (PropCard) |
| PROP-03 | Adjustable stat lines via slider | 03 (LineSlider with 0.5 step) |
| NEWS-03 | News flags visible on player page | 02 (AlertBadge), 03 (NewsList) |

## Decisions Implemented

All 23 locked decisions (D-01 through D-23) are addressed across the 4 plans:

| Decision | Implementation | Plan |
|----------|---------------|------|
| D-01: SPA routing with React Router | BrowserRouter with 3 routes (/, /player/:id, /backtest) | 01 |
| D-02: Local state management | useState/useEffect hooks, no external lib | 02 |
| D-03: Feature-based folder structure | pages/, components/, hooks/, utils/, api/ | 01 |
| D-04: No MUI, custom Tailwind CSS | Tailwind v4 @theme design system, no MUI | 01 |
| D-05: Dark mode only | @custom-variant dark, <html class="dark"> | 01 |
| D-06: Separate hit rate chart per prop | HitRateChart inside PropCard | 03 |
| D-07: Color-coded probability badge | ProbabilityBadge with thresholds | 02 |
| D-08: Half-point slider | LineSlider with step=0.5 | 03 |
| D-09: Polished micro-transitions | CSS keyframes + Tailwind animate | 01, 04 |
| D-10: Compact grid layout | lg:grid-cols-3 md:grid-cols-2 grid-cols-1 | 03 |
| D-11: Game log table below prop cards | GameLogTable in Game Logs tab | 03 |
| D-12: Injury/news badges | AlertBadge next to player name | 02 |
| D-13: Three pages | Home, Player, Backtest routes | 01, 03, 04 |
| D-14: Tabbed player layout | TabBar with Overview/Game Logs/News | 02, 03 |
| D-15: Persistent top navbar | Navbar with logo + search + nav links | 02 |
| D-16: On-demand data fetch | Promise.all per page, no prefetching | 02 |
| D-17: Backtest summary → breakdown → calibration | BacktestPage vertical layout | 04 |
| D-18: Home page search landing | HomePage with empty state message | 03 |
| D-19: Skeleton placeholders and toasts | SkeletonCard/Table + react-hot-toast | 02 |
| D-20: Clean rebuild from scratch | Delete V1 src/ and public/ | 01 |
| D-21: CRA → Vite migration | vite.config.js + @vitejs/plugin-react | 01 |
| D-22: Desktop-first responsive | 3 breakpoints (lg, md, default) | 04 |
| D-23: React Testing Library | Vitest + @testing-library/react | 01 |

## Plan Summary

| Plan | Wave | Objective | Tasks | Files | Autonomous |
|------|------|-----------|-------|-------|------------|
| 07-01 | 1 | Foundation: Vite, Tailwind, Router, Design System | 3 | 12+ | yes |
| 07-02 | 2 | Data Hooks & Navigation Shell | 2 | 16 | yes |
| 07-03 | 3 | Feature Components: Prop Cards, Charts, Pages | 2 | 11 | yes |
| 07-04 | 4 | Backtest Page, Polish & Deployment | 2 | 12 | yes |

## Wave Structure

```
Wave 1: 07-01 — Project foundation (Vite + Tailwind + Router + test infra)
  ↓
Wave 2: 07-02 — Data hooks + navigation + badges + skeletons
  ↓
Wave 3: 07-03 — PropCard + HitRateChart + GameLogTable + PlayerPage + HomePage
  ↓
Wave 4: 07-04 — BacktestPage + backend API + responsive polish + Docker + V1 cleanup
```

## Risk Mitigation: Visx v4 Alpha

**Risk:** Visx v4 alpha (4.0.0-alpha.11) may have breaking changes or bugs since it's pre-release.

**Mitigations:**
1. Pin exact alpha version in package.json (no ^ prefix): `"4.0.0-alpha.11"` 
2. All Visx imports use `@next` tag: `npm install @visx/shape@next @visx/group@next ...`
3. Test Visx rendering early (Plan 03 Task 1 creates HitRateChart)
4. Fallback documented in RESEARCH.md: if critical bugs arise, Recharts can substitute (higher-level but larger bundle)
5. Keep Visx usage minimal: only BarGroup for hit rates, LinePath+Circle for calibration — no exotic features

## Deferred Items (NOT in scope)

Per CONTEXT.md DEFERRED section:
- Daily picks dashboard (PICK-01/02/03) — v2 requirement
- League-wide leaderboard or comparison views
- User accounts / authentication
- Mobile app or PWA
- Light theme toggle
- Push notifications for news alerts
- Sportsbook odds comparison (ODDS-01/02/03)

## API Dependency Note

**Backtest API endpoints do not exist in the backend yet.** Phase 5 (API Layer) created `/api/players/*` and `/api/teams` endpoints, but no `/api/backtest/*` routes. Plan 04 Task 1 creates these endpoints in `server/api/backtest.py` by reading the existing backtest JSON files from `server/data/backtest_logs/`.

## Verification

Overall phase verification:
1. `cd hoopprophet && npm run build` — production build succeeds
2. `cd hoopprophet && npm run test` — all tests pass
3. `grep -r "@mui" hoopprophet/src/ | wc -l` returns 0 (zero V1 dependencies)
4. All 3 pages render: Home, Player, Backtest
5. Visx charts render (hit rate bars, calibration line) without console errors
6. Responsive layout adapts across 3 breakpoints
7. Docker build completes successfully
8. Backend backtest endpoints return valid JSON

## Success Criteria

- V1 monolithic frontend fully replaced by component-based Vite SPA
- Player search with autocomplete works (debounced API calls)
- Prop cards display probability badges, hit rate charts, and adjustable line sliders
- Hit rate charts show L5/L10/L20/Season bars with conditional colors
- Game log table displays recent stats in compact scrollable form
- News/injury badges appear next to player names
- Backtest dashboard shows summary stats, season breakdown, and calibration chart
- Dark mode is permanent (no toggle)
- All 8 micro-transitions animate smoothly
- Responsive design works on desktop, tablet, and mobile
- Production Docker build serves static files