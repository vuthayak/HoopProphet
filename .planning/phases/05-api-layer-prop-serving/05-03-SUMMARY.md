---
phase: 05-api-layer-prop-serving
plan: "03"
subsystem: api
tags: [fastapi, integration-tests, v1-cleanup, dependency-removal]

# Dependency graph
requires:
  - server/api/players.py
  - server/api/teams.py
  - server/services/prediction_service.py
  - server/services/hitrate_service.py
provides:
  - server/tests/test_integration_05.py
  - Clean requirements.txt without V1 dependencies
affects:
  - Phase 06 (frontend integration)
  - Phase 07 (live predictions)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - End-to-end integration tests with FastAPI TestClient
    - V1 dependency cleanup (xgboost, google-generativeai removed)
    - Test isolation via temp SQLite and fixture patterns

key-files:
  created:
    - server/tests/test_integration_05.py - 37 integration tests
  modified:
    - server/requirements.txt - removed xgboost, google-generativeai

key-decisions:
  - "xgboost removed from requirements (replaced by LightGBM in Phase 3)"
  - "google-generativeai removed per CLNP-01 and PROJECT.md 'Drop Gemini summaries'"
  - "Integration tests use temp SQLite DB with seed data, patched via monkeypatch"

patterns-established:
  - "Integration tests mock app.state.model_artifact directly for graceful degradation tests"
  - "V1 cleanup verified programmatically in test suite (TestV1Cleanup class)"

requirements-completed: [PROP-01, PROP-02, PROP-04, PROP-05, PROP-06, CLNP-02, CLNP-03]

# Metrics
duration: ~5min
started: 2026-04-18T15:26:20Z
completed: 2026-04-18T15:30:00Z
tasks: 1
files: 2

---

# Phase 05 Plan 03: Integration Tests, V1 Cleanup, and Full API Verification

**V1 dependencies removed and comprehensive end-to-end integration test suite covering all Phase 5 endpoints**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-18T15:26:20Z
- **Completed:** 2026-04-18T15:30:00Z
- **Tasks:** 1 (auto task with TDD)
- **Files:** 2 (1 modified, 1 new)

## Accomplishments

- Removed V1 dependencies (`xgboost`, `google-generativeai`) from requirements.txt per CLNP-01 and CLNP-02
- Created `test_integration_05.py` with 37 end-to-end tests covering all Phase 5 endpoints
- Verified app.py has no remaining imports from `server.ml`, `nba_api.stats`, or `google.generativeai`
- All Phase 5 requirements verified working: PROP-01 (hit rates), PROP-02 (default lines), PROP-04 (top props), PROP-05 (ML probability), PROP-06 (game logs), CLNP-02 (model artifact loading), CLNP-03 (SQLite cache serving)
- Total Phase 5 test count: 86 tests (37 integration + 49 service/API)

## Task Commits

1. **Task 1: Integration tests, V1 cleanup, and full API verification** - `a631dc5` (feat)
   - GREEN: Removed xgboost and google-generativeai from requirements.txt; created test_integration_05.py
   - Files: server/requirements.txt, server/tests/test_integration_05.py

## Files Created/Modified

- `server/requirements.txt` - Removed `xgboost` (replaced by LightGBM in Phase 3) and `google-generativeai` (Gemini dependency per CLNP-01)
- `server/tests/test_integration_05.py` - 37 end-to-end integration tests

## Test Coverage

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestHealthEndpoint | 4 | D-16: /api/health with model_loaded status |
| TestPlayersList | 2 | PROP-06: player list from cache |
| TestPlayersSearch | 3 | PROP-06: search filtering |
| TestPlayerDetail | 2 | PROP-02: player with default lines |
| TestPlayerProps | 2 | PROP-01/04/05: top props with hit rates |
| TestPlayerPropsNoModel | 2 | D-10: graceful degradation when model absent |
| TestPlayerGamelogs | 3 | PROP-06: game logs with limit |
| TestPlayerHitrates | 3 | PROP-01: L5/L10/L20/season hit rate windows |
| TestPlayerLines | 2 | PROP-02: default lines rounded to 0.5 |
| TestTeamsList | 2 | CLNP-03: team list from cache |
| TestTeamDetail | 1 | CLNP-03: team detail |
| TestUnknownPlayer404 | 4 | D-12: 404 for unknown player IDs |
| TestUnknownTeam404 | 1 | D-12: 404 for unknown team ID |
| TestV1Cleanup | 3 | V1 dependencies removed from requirements.txt |
| TestRouteRegistration | 3 | All routers registered on app |
| **Total** | **37** | |

## Test Results

```
37 passed in 0.65s (test_integration_05.py)
49 passed in 0.62s (all other Phase 5 tests)
86 total Phase 5 tests passing
```

## Deviations from Plan

**None - plan executed exactly as written.**

## Pre-existing Test Isolation Issue

When `test_app_startup.py` runs after `test_player_api.py` in the same session, 2 tests in `test_app_startup.py` fail due to a module import ordering issue. This is a **pre-existing problem** where `test_player_api.py` imports `from server.app import app` at module level, causing the FastAPI lifespan to execute before `test_app_startup.py`'s config patches are applied. This issue does not appear when `test_app_startup.py` runs in isolation (all 7 tests pass). This is unrelated to the Phase 05-03 changes and should be addressed separately by refactoring affected tests to avoid module-level app imports.

## Verification

```bash
# V1 cleanup
grep "xgboost" server/requirements.txt        # CLEAN
grep "google-generativeai" server/requirements.txt  # CLEAN
grep -r "from server.ml" server/app.py        # CLEAN
grep -r "nba_api.stats" server/app.py         # CLEAN

# App loads with all routes
python -c "from server.app import app; print(len(app.routes))"  # 13 routes

# Integration tests
python -m pytest server/tests/test_integration_05.py -x -v  # 37 passed
```

## Next Phase Readiness

- All Phase 5 endpoints fully integrated and tested
- V1 dependencies cleaned up (xgboost, google-generativeai)
- 86 total tests passing across Phase 5 test suite
- API ready for Phase 07 frontend integration

---
*Phase: 05-api-layer-prop-serving*
*Completed: 2026-04-18*
