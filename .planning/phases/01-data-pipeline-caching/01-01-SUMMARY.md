---
phase: 01-data-pipeline-caching
plan: 01
subsystem: database
tags: [sqlite, nba_api, requests-cache, tenacity, pytest, rate-limiting]

requires: []
provides:
  - 7-table SQLite schema via init_db() for game logs, teams, players, stats, rosters, schedules, progress
  - Rate-limited NBAClient with HTTP caching and retry for all NBA API endpoints
  - pytest infrastructure with tmp_db fixture and sample data fixtures
  - Package constants (SEASONS, DB_PATH, CACHE_PATH) at server.pipeline
affects: [01-data-pipeline-caching, 02-feature-engineering]

tech-stack:
  added: [nba_api==1.11.4, requests-cache==1.3.1, tenacity>=9.0.0, pytest>=8.0.0, pytest-timeout>=2.2.0, tqdm>=4.66.0]
  patterns: [dual-layer-caching, rate-limited-api-client, resumable-progress-tracking, WAL-mode-sqlite]

key-files:
  created:
    - server/pipeline/__init__.py
    - server/pipeline/db/schema.py
    - server/pipeline/db/connection.py
    - server/pipeline/db/queries.py
    - server/pipeline/nba_client.py
    - server/tests/conftest.py
    - server/tests/test_db.py
    - server/tests/test_nba_client.py
    - pyproject.toml
  modified:
    - server/requirements.txt
    - .gitignore

key-decisions:
  - "Used NBAStatsHTTP.set_session() instead of NBAHTTP — nba_api 1.11.4 exports NBAStatsHTTP not NBAHTTP"
  - "Foreign key enforcement enabled on all connections — ensures referential integrity between game logs and players"
  - "INSERT OR IGNORE for game logs, INSERT OR REPLACE for players/teams — dedup strategy matches entity semantics"

patterns-established:
  - "WAL mode + foreign keys enabled on every connection via get_connection()"
  - "Tenacity @retry decorator on every API fetch method with exponential backoff + jitter"
  - "tmp_db pytest fixture pattern for isolated database tests"

requirements-completed: [DATA-01, DATA-03, DATA-04]

duration: 6min
completed: 2026-03-23
---

# Phase 01 Plan 01: Foundation - DB, API Client, Tests Summary

**7-table SQLite schema with WAL mode, rate-limited NBAClient using requests-cache + tenacity retry, and pytest infrastructure with 10 passing tests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-23T01:32:23Z
- **Completed:** 2026-03-23T01:39:01Z
- **Tasks:** 3
- **Files modified:** 17

## Accomplishments
- Complete SQLite database layer with 7 tables, 3 indexes, and full CRUD query functions
- NBAClient with 600ms rate limiting, 5-attempt exponential backoff retry, and HTTP response caching via requests-cache
- pytest infrastructure with shared fixtures (tmp_db, sample data) and 10 passing tests covering DB operations and API client behavior
- All Phase 1 Python dependencies installed and verified

## Task Commits

Each task was committed atomically:

1. **Task 1: Dependencies, Package Structure, and Config** - `701a0d3` (chore)
2. **Task 2: SQLite Database Layer and Test Infrastructure** - `3aaa569` (feat)
3. **Task 3: Rate-Limited NBA API Client with HTTP Caching and Retry** - `2c7e30a` (feat)

## Files Created/Modified
- `server/requirements.txt` - Pinned Phase 1 dependencies (nba_api, requests-cache, tenacity, pytest)
- `pyproject.toml` - pytest configuration with testpaths and timeout
- `.gitignore` - Added SQLite, __pycache__, .pytest_cache patterns
- `server/pipeline/__init__.py` - SEASONS, DB_PATH, CACHE_PATH constants
- `server/pipeline/db/schema.py` - 7-table DDL with init_db() function
- `server/pipeline/db/connection.py` - WAL-mode connection factory with FK enforcement
- `server/pipeline/db/queries.py` - Insert/upsert/progress query functions for all tables
- `server/pipeline/nba_client.py` - NBAClient class with rate limiting, caching, retry
- `server/tests/conftest.py` - Shared pytest fixtures (tmp_db, sample_game_log_df, sample_team_stats_df)
- `server/tests/test_db.py` - 5 DB tests (schema, upsert, progress, dedup, WAL)
- `server/tests/test_nba_client.py` - 5 API client tests (rate limit, retry, session, empty response, static data)

## Decisions Made
- **NBAStatsHTTP vs NBAHTTP:** nba_api 1.11.4 exports `NBAStatsHTTP` not `NBAHTTP` as referenced in older docs/PRs. Used `NBAStatsHTTP.set_session()` for session injection.
- **Foreign key enforcement:** Enabled on every connection to ensure data integrity. Tests seed player records before inserting game logs.
- **Dedup strategy:** `INSERT OR IGNORE` for game logs (append-only), `INSERT OR REPLACE` for players/teams (mutable entities).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed NBAHTTP import to NBAStatsHTTP**
- **Found during:** Task 3
- **Issue:** Plan specified `from nba_api.stats.library.http import NBAHTTP` but nba_api 1.11.4 exports `NBAStatsHTTP`
- **Fix:** Changed import to `NBAStatsHTTP` and updated `set_session()` call
- **Files modified:** server/pipeline/nba_client.py
- **Verification:** Import succeeds, test_cached_session_injected passes
- **Committed in:** 2c7e30a

**2. [Rule 1 - Bug] Fixed FK constraint violation in test_insert_game_log_dedup**
- **Found during:** Task 2
- **Issue:** Test inserted game logs without seeding the referenced player, causing FOREIGN KEY constraint failure
- **Fix:** Added `_seed_player()` helper to insert player record before game log insertion
- **Files modified:** server/tests/test_db.py
- **Verification:** test_insert_game_log_dedup passes
- **Committed in:** 3aaa569

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DB schema ready for Plans 02 and 03 to store collected data
- NBAClient ready for data collection scripts
- pytest infrastructure ready for additional test files
- All imports verified — no circular dependencies

## Self-Check: PASSED

All 11 created files verified present. All 3 task commits verified in git log.

---
*Phase: 01-data-pipeline-caching*
*Completed: 2026-03-23*
