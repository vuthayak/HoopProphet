---
phase: 05-api-layer-prop-serving
plan: "01"
subsystem: api
tags: [fastapi, sqlite, lifespan, model-serving, cors]

# Dependency graph
requires: []
provides:
  - server/core/config.py exports DB_PATH, MODEL_ARTIFACT_PATH, API_HOST, API_PORT, CORS_ORIGINS
  - server/services/player_service.py exports get_players, search_players, get_player_by_id, get_player_game_logs
  - server/services/team_service.py exports get_teams, get_team_by_id
  - server/app.py V2 FastAPI with lifespan model preloading, /api/health, CORS middleware
affects:
  - Phase 05 subsequent plans (players/teams routers)
  - Phase 06 (prop predictions, hit rates)
  - Phase 07 (frontend integration)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lifespan context manager for FastAPI startup/shutdown
    - Service layer reading from SQLite via existing queries.py functions
    - CORS middleware with configurable origins from config.py
    - Graceful degradation when model artifact is absent (D-10)

key-files:
  created:
    - server/core/__init__.py - Empty package init
    - server/core/config.py - Centralized config re-exporting from pipeline
    - server/services/__init__.py - Empty package init
    - server/services/player_service.py - Player data queries from SQLite
    - server/services/team_service.py - Team data queries from SQLite
    - server/tests/test_app_startup.py - 7 tests for lifespan and health
    - server/tests/test_player_service.py - 11 tests for player service
    - server/tests/test_team_service.py - 5 tests for team service
  modified:
    - server/app.py - Complete rewrite to V2 (removed V1 ml.*, nba_api.* imports)
    - server/pipeline/db/queries.py - get_players_df now includes is_active column

key-decisions:
  - "server/core/config.py imports DB_PATH from server.pipeline and MODEL_ARTIFACT_PATH from server.pipeline.train_config rather than duplicating path computation"
  - "player_service checks 'is_active' column exists before filtering to handle test DBs that omit it"
  - "Graceful degradation: app starts and serves player/team/game-log endpoints even when model artifact is absent (D-10)"

patterns-established:
  - "Pattern: SQLite connection per request via context manager (get_connection used in `with` blocks)"
  - "Pattern: Service layer functions return list[dict] for list endpoints and single dict for get_by_id, raising ValueError for unknown IDs"
  - "Pattern: FastAPI lifespan context manager handles startup/shutdown; health endpoint reads app.state.model_artifact"

requirements-completed: [CLNP-02, CLNP-03, PROP-06]

# Metrics
duration: 7min
started: 2026-04-18T14:58:38Z
completed: 2026-04-18T15:05:00Z
tasks: 1
files: 10

---

# Phase 05 Plan 01: API Foundation Summary

**V2 FastAPI with model artifact preloading at startup and SQLite-backed player/team/game-log services replacing V1 live NBA API calls**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-18T14:58:38Z
- **Completed:** 2026-04-18T15:05:00Z
- **Tasks:** 1 (1 auto task with TDD sub-phases)
- **Files:** 10 (2 modified, 8 new)

## Accomplishments

- Replaced V1 per-request training and live NBA API calls with SQLite-backed services
- Model artifact now loads once at FastAPI lifespan startup with graceful degradation when artifact is missing
- Centralized config (`server/core/config.py`) exposing DB_PATH, MODEL_ARTIFACT_PATH, CORS_ORIGINS, API_HOST, API_PORT
- All 23 new tests passing (test_app_startup.py: 7, test_player_service.py: 11, test_team_service.py: 5)
- `/api/health` endpoint returns model_loaded status per D-16

## Task Commits

1. **Task 1: Core config, SQLite-backed services, and refactored app.py with model preloading** - `6b9e7f1` (feat)
   - RED: Added test files (23 tests — all initially failing as expected)
   - GREEN: Implemented config, services, rewritten app.py, fixed get_players_df is_active column
   - Files: server/core/__init__.py, server/core/config.py, server/services/__init__.py, server/services/player_service.py, server/services/team_service.py, server/app.py, server/pipeline/db/queries.py, server/tests/test_app_startup.py, server/tests/test_player_service.py, server/tests/test_team_service.py

## Files Created/Modified

- `server/core/__init__.py` - Empty package init
- `server/core/config.py` - Centralized config re-exporting DB_PATH, MODEL_ARTIFACT_PATH, CORS_ORIGINS, API_HOST, API_PORT from pipeline modules
- `server/services/__init__.py` - Empty package init
- `server/services/player_service.py` - get_players, search_players, get_player_by_id, get_player_game_logs — all reading from SQLite via queries.py
- `server/services/team_service.py` - get_teams, get_team_by_id — reading from SQLite via queries.py
- `server/app.py` - V2 FastAPI with lifespan model preloading, /api/health, CORS. All V1 imports (ml.*, nba_api.*) removed. No per-request training.
- `server/pipeline/db/queries.py` - get_players_df now includes `is_active` column so active_only filtering works
- `server/tests/test_app_startup.py` - 7 tests for lifespan model loading, graceful degradation, /api/health structure
- `server/tests/test_player_service.py` - 11 tests for get_players/search/get_by_id/get_game_logs with in-memory DB
- `server/tests/test_team_service.py` - 5 tests for get_teams/get_team_by_id with in-memory DB

## Decisions Made

- Re-exported DB_PATH from `server.pipeline` in `server/core/config.py` rather than duplicating path computation — keeps paths in one place (pipeline)
- Service functions return `list[dict]` for list operations and `dict` for single-item lookups, raising `ValueError` with message `"Player/Team not found: {id}"` for unknown IDs
- `get_players_df` query updated to include `is_active` column so `active_only=True` filtering works correctly
- Test fixtures create temp SQLite files (not :memory:) so patching `DB_PATH` via monkeypatch works cleanly across service imports

## Deviations from Plan

**None - plan executed exactly as written**

## Issues Encountered

- **V1 artifact file can't be loaded in tests:** The fake `model.joblib` written to a temp path can't be unpickled by `joblib.load`. Fixed by mocking `load_artifact` to return a dict artifact in `client_with_artifact` fixture instead of relying on real joblib deserialization.
- **`is_active` column missing in `get_players_df`:** The original query didn't include `is_active`, so `active_only` filtering always returned all players. Fixed by updating the SQL query to include `is_active` column and adding a defensive check in service code for when the column is absent.
- **Module-level patching complexity:** Python caches module imports, so patching `MODEL_ARTIFACT_PATH` at different import paths (core/config, pipeline/artifact, pipeline/train_config) was needed because `load_artifact` reads from its own module-level constant.

## Next Phase Readiness

- `server/app.py` V2 structure ready for player/team routers (Plan 02)
- `/api/players` and `/api/teams` router placeholders already registered with try/except ImportError
- SQLite services ready for prop-line and hit-rate endpoints (Plan 03)
- Model artifact preloading in lifespan ready for prediction endpoints

---
*Phase: 05-api-layer-prop-serving*
*Completed: 2026-04-18*
