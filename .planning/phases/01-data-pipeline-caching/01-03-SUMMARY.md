---
phase: 01-data-pipeline-caching
plan: 03
subsystem: database
tags: [sqlite, nba_api, dnp-synthesis, cli, integration-tests, resumable-pipeline]

requires:
  - phase: 01-data-pipeline-caching (plan 01)
    provides: "NBAClient, SQLite schema, DB queries, pytest infrastructure"
  - phase: 01-data-pipeline-caching (plan 02)
    provides: "collect_team_rosters, collect_team_schedules, collect_team_stats, collect_player_gamelogs"
provides:
  - "synthesize_dnp_rows — creates zero-minute rows via roster × schedule × gamelogs cross-reference"
  - "synthesize_all_dnp_rows — runs DNP synthesis across all seasons"
  - "CLI orchestrator with --full, --refresh, --validate modes and Ctrl+C handling"
  - "Integration tests for pipeline resumability and data validation"
affects: [02-feature-engineering, 03-model-training]

tech-stack:
  added: []
  patterns: [trade-aware-dnp-synthesis, resumable-collection, completeness-validation]

key-files:
  created:
    - server/pipeline/processors/dnp_synthesis.py
    - server/tests/test_dnp_synthesis.py
  modified:
    - server/pipeline/ingest.py
    - server/tests/test_ingest.py

key-decisions:
  - "Infer player team tenure from game log MATCHUP column — handles mid-season trades correctly"
  - "Single-team players extend tenure to team's last scheduled game — captures late-season DNPs"
  - "Multi-team players constrain tenure to actual game log date range — avoids false DNP rows"
  - "DNP synthesis uses INSERT OR IGNORE — idempotent, safe to re-run"
  - "Validation thresholds: 30 teams, 400+ players, 100+ team stats, 50K+ game logs"

patterns-established:
  - "Trade-aware DNP synthesis: only create DNP rows within player's confirmed team tenure"
  - "CLI orchestrator: seeds teams → seeds players → runs collectors in dependency order → synthesizes DNP → validates"
  - "validate_completeness() checks all tables and reports per-season + per-status counts"

requirements-completed: [DATA-01, DATA-02, DATA-04, DATA-05]

duration: 5min
completed: 2026-04-18
---

# Phase 01 Plan 03: DNP Synthesis & CLI Orchestrator Summary

**DNP row synthesis via roster × schedule × game log cross-reference, CLI orchestrator with --full/--refresh/--validate modes, and integration tests proving resumability and validation**

## Performance

- **Duration:** 5 min (original execution: 2026-03-23)
- **Started:** 2026-03-23T01:39:28Z
- **Completed:** 2026-03-23T01:45:02Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- DNP synthesis processor creates zero-minute rows for every game where a rostered player didn't play, correctly handling mid-season trades by inferring team tenure from game log MATCHUP data
- CLI orchestrator (`python -m server.pipeline.ingest`) runs full 5-season collection, incremental refresh, or validation-only mode with Ctrl+C graceful handling
- Integration tests prove pipeline is resumable (only fetches uncompleted items), validation catches incomplete datasets, and all tables populate correctly

## Task Commits

Each task was committed atomically:

1. **Task 1: DNP Row Synthesis Processor** - `04c3bc2` (feat)
2. **Task 2: CLI Ingest Orchestrator** - `1cef6f5` (feat)
3. **Task 3: Integration Tests for Pipeline and Resumability** - `8a5a772` (test)

**Plan metadata:** `2eb423f` (docs: complete DNP synthesis & CLI orchestrator plan)

## Files Created/Modified
- `server/pipeline/processors/dnp_synthesis.py` - Trade-aware DNP synthesis via roster × schedule × game log cross-reference; `synthesize_dnp_rows()` and `synthesize_all_dnp_rows()` functions
- `server/tests/test_dnp_synthesis.py` - 4 tests: DNP rows created, no false DNP for traded player, idempotency, no DNP for player with no game logs
- `server/pipeline/ingest.py` - CLI orchestrator with `--full`, `--refresh`, `--validate`, `--features-only`, `--features`, `-v` flags; `validate_completeness()` checks all table counts
- `server/tests/test_ingest.py` - 6 tests: game logs stored, team stats stored, resume after interrupt, validate insufficient data, validate sufficient data, full pipeline mock

## Decisions Made
- **Trade handling via MATCHUP column:** `_get_player_team_tenure()` parses the team abbreviation from game log MATCHUP strings (format "TEA vs. OPP" or "TEA @ OPP"), grouping consecutive games by team to determine date ranges. For multi-team players, tenure is bounded to actual game log dates; single-team players extend to the team's last scheduled game.
- **Idempotent DNP insertion:** Uses `INSERT OR IGNORE` so re-running synthesis doesn't create duplicates.
- **Validation thresholds:** teams≥30, players≥400, team_stats≥100, game_logs_real≥50000.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria met.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all components are fully wired. DNP synthesis uses existing collectors' output, ingest CLI orchestrates all collectors, tests mock NBAClient.

## Next Phase Readiness

- Phase 01 data pipeline complete: teams, players, rosters, schedules, team stats, player game logs, and synthesized DNP rows all available in SQLite
- Feature engineering (Phase 2) can read from `hoopprophet.db` via `server/pipeline/db/queries.py`
- `python -m server.pipeline.ingest --full` ready for production data collection
- `python -m server.pipeline.ingest --validate` ready for data quality checks

## Self-Check: PASSED

- All 4 DNP synthesis tests pass (4/4)
- All 6 ingest tests pass (6/6)
- Full test suite: 120 passed
- `python -m server.pipeline.ingest --help` shows all modes
- `python -m server.pipeline.ingest --validate` runs and reports validation (empty DB as expected)
- All acceptance criteria verified:
  - `dnp_synthesis.py` contains `synthesize_dnp_rows`, `synthesize_all_dnp_rows`, `is_dnp`, `_get_player_team_tenure`, `INSERT OR IGNORE`
  - `ingest.py` contains `main`, `argparse.ArgumentParser`, `--full`, `--refresh`, `--validate`, `validate_completeness`, `_get_current_season`, `KeyboardInterrupt`, `logging.basicConfig`, `os.makedirs`, `init_db`
  - `test_ingest.py` contains `_create_mock_client`, `test_gamelogs_stored`, `test_team_stats_stored`, `test_resume_after_interrupt`, `test_validates_insufficient_data`, `test_validates_sufficient_data`, `test_full_pipeline_mock`, `MagicMock`

---
*Phase: 01-data-pipeline-caching*
*Completed: 2026-04-18*