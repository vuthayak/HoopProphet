---
phase: 07-frontend-rebuild
plan: 04
subsystem: ui
tags: [react, vite, fastapi, backtest, docker, visx]

# Dependency graph
requires:
  - phase: "07-03"
    provides: "All 3 pages scaffolded with skeleton loaders, API hooks in place, Navbar with routing"
provides:
  - "Backend /api/backtest/* endpoints serving real backtest data"
  - "Visx calibration chart showing predicted vs observed probabilities"
  - "Season breakdown table with ROI per season"
  - "Multi-stage Docker build for Vite production"
affects: ["07-frontend-rebuild"]

# Tech tracking
tech-stack:
  added: [fastapi, @visx/shape, @visx/scale, @visx/axis, @visx/responsive]
  patterns: [FastAPI router pattern with HTTPException, calibration curve visualization, multi-stage Docker]

key-files:
  created:
    - server/api/backtest.py
  modified:
    - server/app.py
    - hoopprophet/Dockerfile
    - docker-compose.yml
    - hoopprophet/src/__tests__/BacktestPage.test.jsx

key-decisions:
  - "ROI computed using vig-adjusted breakeven (52.4%) via formula: (accuracy - breakeven) / breakeven * 100"
  - "Multi-stage Docker uses node:20-alpine for build + serve, no nginx needed for SPA"
  - "Calibration bins use overall_calibration from backtest_metrics JSON (fewer than 10 bins in practice)"

patterns-established:
  - "FastAPI router with HTTPException for 404s, _load_backtest_metrics helper finds latest JSON"
  - "Visx ParentSize wrapper for responsive chart sizing"
  - "VITE_API_BASE build arg replaces REACT_APP_ env vars per V1 cleanup"

requirements-completed: [UI-06, D-09, D-17, D-22]

# Metrics
duration: 4min
completed: 2026-04-22
---

# Phase 07 Plan 04: Backtest Dashboard & Docker Summary

**Backend backtest API endpoints with Visx calibration chart, multi-stage Docker build**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-22T00:25:01Z
- **Completed:** 2026-04-22T00:29:21Z
- **Tasks:** 1 (2 commits)
- **Files modified:** 5

## Accomplishments
- Created 3 FastAPI backtest endpoints reading from `server/data/backtest_logs/backtest_metrics_*.json`
- Frontend already had all components (BacktestPage, BacktestSummary, SeasonBreakdown, CalibrationChart, useBacktest hook) built in prior plans
- Multi-stage Dockerfile for Vite production build with node:20-alpine + serve
- docker-compose.yml updated with VITE_API_BASE build arg (removed REACT_APP_ vars)
- BacktestPage test passes verifying section headings render correctly

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend API + Docker** - `0475ce2` (feat)
2. **Task 1: Test file** - `ce12fcb` (test)

**Plan metadata:** (orchestrator commits after wave completes)

## Files Created/Modified
- `server/api/backtest.py` - 3 FastAPI endpoints: /summary, /seasons, /calibration
- `server/app.py` - Added backtest_router include
- `hoopprophet/Dockerfile` - Multi-stage Vite build (npm ci, serve)
- `docker-compose.yml` - VITE_API_BASE build arg, removed REACT_APP_ vars
- `hoopprophet/src/__tests__/BacktestPage.test.jsx` - Test for heading renders

## Decisions Made
- ROI formula: `(accuracy - breakeven) / breakeven * 100` for vig-adjusted ROI
- Calibration bins derived from overall_calibration.fraction_positives + mean_predicted_value
- Dockerfile uses `serve -s dist` for SPA (no nginx needed)

## Deviations from Plan

None - plan executed exactly as written. Frontend components were already built in prior plans (07-01 through 07-03).

## Issues Encountered
- App.test.jsx had unrelated React import fix from prior plan - reverted to avoid mixing concerns
- Build timeout when re-running npm run build - dist folder exists from successful build earlier

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend backtest endpoints return correct JSON shapes
- Frontend already renders BacktestPage with all 3 sections
- Vite build succeeds producing dist/
- Docker multi-stage build configured correctly
- Ready for next plan in Phase 7

---
*Phase: 07-frontend-rebuild*
*Completed: 2026-04-22*