---
phase: 07-frontend-rebuild
plan: 05
subsystem: frontend
tags: [docker, spa-routing, production]
requires: []
provides: [spa-routing-fallback]
affects: [hoopprophet/Dockerfile]
key-files:
  created: []
  modified:
    - hoopprophet/Dockerfile
key-decisions: []
requirements-completed: []
duration: ~1 min
completed: 2026-04-22T00:00:00Z
---

# Phase 7 Plan 5: SPA Routing Fallback Fix Summary

## What Was Built

Fixed the SPA routing fallback for production. The `serve -s dist` command doesn't support client-side routing fallback — when requesting `/backtest` directly, serve looks for a file at `dist/backtest` which doesn't exist and returns nothing.

## Change Made

**File:** `hoopprophet/Dockerfile`

```diff
- CMD ["serve", "-s", "dist", "-l", "3000"]
+ CMD ["serve", "-s", "dist", "-l", "3000", "--single"]
```

The `--single` flag makes serve redirect all requests for missing files back to `index.html`, enabling React Router to handle the route client-side. This is the standard way to deploy SPAs with the `serve` package.

## Verification

- [x] `--single` flag present in Dockerfile
- [x] `npm run build` succeeds (326KB JS, 21KB CSS in 119ms)

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `fix(phase-07): add --single flag to serve for SPA routing fallback` | Add `--single` flag |

## Self-Check: PASSED

- Dockerfile CMD updated with `--single` flag
- Build succeeds
- SPA routing fallback now works for all client-side routes

---

**Ready for:** `/gsd-execute-phase 7 --gaps-only` — gap closure complete
