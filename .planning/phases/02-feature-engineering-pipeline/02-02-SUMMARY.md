---
phase: 02-feature-engineering-pipeline
plan: 02
subsystem: testing
tags: [pandas, feature-engineering, contextual-features, matchup-history, pytest]
requires:
  - phase: 02-01
    provides: rolling feature columns and phase 2 test fixture data
provides:
  - contextual game features (rest days, b2b, home/away, defense, pace, position)
  - matchup history averages within current + previous season window
  - unit test coverage validating contextual and matchup feature correctness
affects: [phase-03-model-training-calibration]
tech-stack:
  added: []
  patterns: [player-date grouped diff for rest days, merge-based matchup history aggregation]
key-files:
  created:
    - server/pipeline/processors/contextual_features.py
    - server/pipeline/processors/matchup_features.py
    - server/tests/test_contextual_features.py
  modified:
    - server/pipeline/processors/matchup_features.py
key-decisions:
  - "Use matchup string parsing plus team abbreviation mapping for opponent/team joins."
  - "Compute matchup averages via merge+groupby over prior games constrained to current and previous season."
patterns-established:
  - "Contextual features are merged from team_stats by season and parsed team IDs."
  - "Matchup features remain NaN when no prior history exists for a player-opponent pair."
requirements-completed: [FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-08]
duration: 18 min
completed: 2026-03-23
---

# Phase 2 Plan 2: Contextual and Matchup Features Summary

**Contextual schedule/opponent features and two-season matchup history averages are now computed and covered by dedicated unit tests.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-23T03:00:00Z
- **Completed:** 2026-03-23T03:18:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `compute_contextual_features()` to produce rest/B2B, home/away, opponent/team pace, opponent defense, and position columns.
- Added `compute_matchup_features()` to generate `matchup_avg_{stat}` columns for all `PRIMARY_STATS` using prior games only in a 2-season window.
- Added 10 passing tests in `server/tests/test_contextual_features.py` and validated no regression in `server/tests/test_rolling_features.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Contextual Features Processor + Matchup Features Processor** - `b8173bd` (feat)
2. **Task 2: Contextual & Matchup Features Tests** - `e72b260` (test)

## Files Created/Modified
- `server/pipeline/processors/contextual_features.py` - Contextual feature computation and opponent/team extraction helpers.
- `server/pipeline/processors/matchup_features.py` - Matchup history aggregation with season-window constraints.
- `server/tests/test_contextual_features.py` - End-to-end processor tests for contextual and matchup behavior.

## Decisions Made
- Used parsed `matchup` abbreviations with `teams` lookup to derive `opp_team_id` and `player_team_id`.
- Kept matchup history features as NaN for first meetings so downstream LightGBM can handle missing values naturally.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected opponent abbreviation mapping alignment in matchup history**
- **Found during:** Task 2 (test verification)
- **Issue:** Opponent abbreviation mapping in historical logs could misalign IDs, producing incorrect matchup averages.
- **Fix:** Built mapping from deduplicated `(opp_abbr, opp_team_id)` pairs with non-null constraints before applying to history rows.
- **Files modified:** `server/pipeline/processors/matchup_features.py`
- **Verification:** `python -m pytest server/tests/test_contextual_features.py -x -v`
- **Committed in:** `e72b260`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix was required for correctness of matchup averages and fully aligned output with plan requirements.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 Plan 2 deliverables are complete and verified.
- Feature processors are ready for integration with target generation and parquet orchestration in `02-03`.

## Known Stubs
None.

## Self-Check: PASSED

- Verified `02-02-SUMMARY.md` exists in phase directory.
- Verified task commits `b8173bd` and `e72b260` exist in git history.
