---
phase: 01-data-pipeline-caching
plan: 02
subsystem: database
tags: [nba-api, sqlite, data-collection, etl, tqdm, pandas]

requires:
  - phase: 01-data-pipeline-caching (plan 01)
    provides: "NBAClient, SQLite schema, DB queries, collection_progress table"
provides:
  - "collect_team_rosters — seeds teams/players tables and roster associations"
  - "collect_team_schedules — stores game IDs, dates, matchups per team per season"
  - "collect_team_stats — stores DEF_RATING, OFF_RATING, NET_RATING, PACE per team per season"
  - "collect_player_gamelogs — stores per-player per-season game logs with column mapping"
affects: [01-data-pipeline-caching plan 03, 02-feature-engineering]

tech-stack:
  added: [tqdm]
  patterns: [collector-per-entity, progress-tracking-per-item, continue-on-failure]

key-files:
  created:
    - server/pipeline/collectors/rosters.py
    - server/pipeline/collectors/schedules.py
    - server/pipeline/collectors/team_stats.py
    - server/pipeline/collectors/game_logs.py
  modified: []

key-decisions:
  - "Roster collector seeds teams table before schedule/stats collectors depend on it"
  - "Team stats uses entity_id=0 since collection is per-season not per-team"
  - "Game log collector uses per-season calls (not SeasonAll.all) for granular progress"
  - "Column validation in team_stats — fails fast on missing DEF_RATING/PACE columns"

patterns-established:
  - "Collector pattern: (client, conn, seasons) signature returning counts dict"
  - "Progress tracking: check completed set → build work list → iterate remaining"
  - "Error handling: try/except per-item with mark_progress('failed'), continue"

requirements-completed: [DATA-01, DATA-02, DATA-04]

duration: 2min
completed: 2026-03-23
---

# Phase 01 Plan 02: Data Collectors Summary

**Four NBA data collectors (rosters, schedules, team stats, player game logs) with per-item progress tracking and resumable execution via collection_progress table**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T01:41:33Z
- **Completed:** 2026-03-23T01:43:28Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Built 3 team-level collectors: rosters (150 API calls), schedules (150 calls), advanced stats (5 calls)
- Built player game log collector covering all 450+ active players across 5 seasons with column mapping
- All collectors track progress per (entity_id, season) for interrupt/resume capability
- All collectors handle per-item failures gracefully without stopping the pipeline

## Task Commits

Each task was committed atomically:

1. **Task 1: Team Data Collectors (Rosters, Schedules, Advanced Stats)** - `32c028a` (feat)
2. **Task 2: Player Game Log Collector with Resumable Progress** - `1430e4b` (feat)

## Files Created/Modified
- `server/pipeline/collectors/rosters.py` - Fetches team rosters, seeds teams/players tables, tracks per (team, season)
- `server/pipeline/collectors/schedules.py` - Fetches team schedules from LeagueGameFinder, stores GAME_ID/DATE/MATCHUP/WL
- `server/pipeline/collectors/team_stats.py` - Fetches advanced team stats (DEF_RATING, PACE) with column validation
- `server/pipeline/collectors/game_logs.py` - Fetches per-player per-season game logs, maps NBA API columns, parses MM:SS minutes

## Decisions Made
- Roster collector seeds the teams table first so schedule/stats collectors can read from it
- Team stats uses entity_id=0 in collection_progress since the API returns all 30 teams per season call
- Game log collector uses per-season calls (not SeasonAll.all) per research recommendation for smaller responses and better progress tracking
- Column validation in team_stats fails fast with informative error on missing DEF_RATING/PACE

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all collectors are fully wired to NBAClient and queries module.

## Next Phase Readiness
- All 4 collectors ready to be orchestrated by the ingest CLI (Plan 03)
- Plan 03 can call collectors in order: rosters → schedules → team_stats → game_logs
- collection_progress table enables any collector to be re-run safely after interruption

## Self-Check: PASSED

- All 4 collector files exist on disk
- Commit 32c028a (Task 1) verified in git log
- Commit 1430e4b (Task 2) verified in git log
- All imports succeed
- All 10 Plan 01 tests pass

---
*Phase: 01-data-pipeline-caching*
*Completed: 2026-03-23*
