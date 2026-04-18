---
phase: 04-back-testing-engine
plan: "03"
subsystem: testing
tags: [lightgbm, backtesting, cli, parquet, json, walk-forward]

# Dependency graph
requires:
  - phase: 04-back-testing-engine
    provides: run_backtest, BacktestResult, backtest_metrics.py
provides:
  - server/pipeline/backtest_cli.py — CLI orchestration with JSON + Parquet output
  - server/tests/test_backtest_cli.py — 9 integration tests covering all behavior specs
affects: [05-api]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD (RED/GREEN/REFACTOR), CLI orchestration following train_cli.py pattern]

key-files:
  created:
    - server/pipeline/backtest_cli.py
    - server/tests/test_backtest_cli.py
  modified:
    - server/pipeline/backtest_config.py (added MIN_TRAIN_SEASONS, BACKTEST_METRICS_DIR)

key-decisions:
  - "Used timestamp-based file naming: backtest_metrics_{timestamp}.json, backtest_predictions_{timestamp}.parquet"
  - "output_dir parameter overrides both metrics and predictions output directories"
  - "backtest_metadata.n_predictions_per_stat uses stat_type integer codes (string conversion for future name mapping)"

patterns-established:
  - "CLI follows train_cli.py pattern: argparse, logging.basicConfig, sys.exit codes, FileNotFoundError + Exception handling"
  - "JSON output structure mirrors D-01 contract: backtest_metadata, fold_metrics, season_breakdown, overall_calibration, per_stat_calibration, roi, confidence_intervals"

requirements-completed:
  - TEST-01
  - TEST-02
  - TEST-03
  - TEST-04

# Metrics
duration: 2min
completed: 2026-04-18
---

# Phase 4 Plan 03: Back-Test CLI Summary

**CLI orchestration wiring backtest.py and backtest_metrics.py, producing JSON metrics report and Parquet per-prediction output — all 9 tests passing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-18T05:49:37Z
- **Completed:** 2026-04-18T05:51:47Z
- **Tasks:** 1 TDD task (RED/GREEN/REFACTOR)
- **Files created:** 2 (backtest_cli.py, test_backtest_cli.py)
- **Files modified:** 1 (backtest_config.py)

## Accomplishments

- `run_backtest_pipeline` wires `run_backtest` + all 5 metrics functions into a single callable
- JSON output saved to `BACKTEST_METRICS_DIR/backtest_metrics_{timestamp}.json` with full D-01 contract
- Parquet per-prediction output saved to `BACKTEST_METRICS_DIR/backtest_predictions_{timestamp}.parquet`
- `main()` CLI follows `train_cli.py` pattern: `--backtest`, `--parquet-path`, `--output-path`, `--min-train-seasons`, `--output-dir`, `-v`
- 9 integration tests covering all 6 behavior specs: pipeline returns, CLI help, JSON structure, Parquet columns and round-trip

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: test(04-back-testing-engine-03)** — `6f7b32f` (test)
   - 9 failing test cases written before implementation
2. **Task 1 GREEN: feat(04-back-testing-engine-03)** — `0856c6d` (feat)
   - backtest_cli.py with run_backtest_pipeline and main functions
3. **Task 1 REFACTOR: refactor(04-back-testing-engine-03)** — `95e3b3f` (refactor)
   - Replaced deprecated datetime.utcnow() with timezone-aware datetime.now(timezone.utc)

**Plan metadata:** `7fcae98` (docs: complete plan — Phase 4 Plan 02, already existed)

## Files Created/Modified

- `server/pipeline/backtest_cli.py` — CLI orchestration: run_backtest_pipeline, main; imports from backtest.py, backtest_metrics.py, backtest_config.py
- `server/tests/test_backtest_cli.py` — 9 tests: 2 pipeline tests, 3 CLI help tests, 2 JSON structure tests, 2 Parquet tests
- `server/pipeline/backtest_config.py` — Added MIN_TRAIN_SEASONS=2 and BACKTEST_METRICS_DIR (Rule 3 auto-fix — blocking import error)

## Decisions Made

- **Timestamp naming:** `backtest_metrics_{timestamp}.json` and `backtest_predictions_{timestamp}.parquet` ensures unique files per run
- **output_dir overrides both:** Passing `--output-dir` sets both metrics and predictions output directories simultaneously
- **stat_type as integer:** `n_predictions_per_stat` uses integer stat_type codes; name mapping deferred to future phase

## Deviations from Plan

None - plan executed exactly as written.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] backtest_config.py missing MIN_TRAIN_SEASONS and BACKTEST_METRICS_DIR**
- **Found during:** GREEN phase (test collection)
- **Issue:** `backtest.py` imports `MIN_TRAIN_SEASONS` and `BACKTEST_METRICS_DIR` from `backtest_config.py`, but only 6 constants existed (VIG_MULTIPLIER, BREAKEVEN_THRESHOLD, CALIBRATION_BINS, CONFIDENCE_LEVEL, BOOTSTRAP_SAMPLES, DATA_DIR was in backtest.py instead)
- **Fix:** Added `MIN_TRAIN_SEASONS = 2` and `BACKTEST_METRICS_DIR = os.path.join(DATA_DIR, "backtest_logs")` to backtest_config.py; imported DATA_DIR from server.pipeline
- **Files modified:** server/pipeline/backtest_config.py
- **Verification:** Import succeeds, all 9 tests pass
- **Committed in:** 0856c6d (GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was a correctness requirement — the backtest pipeline could not run without the missing constants. No scope creep.

## Issues Encountered

None — all issues resolved via deviation rules.

## Verification Results

| Check | Result |
|-------|--------|
| `python -m pytest server/tests/test_backtest_cli.py -x` | PASSED (9/9) |
| `from server.pipeline.backtest_cli import run_backtest_pipeline, main` | PASSED |
| `python -m server.pipeline.backtest_cli --help` | PASSED — shows --backtest, --parquet-path, --output-path, --min-train-seasons, --output-dir, -v |
| JSON output includes backtest_metadata, fold_metrics, season_breakdown, overall_calibration, per_stat_calibration, roi, confidence_intervals | PASSED |
| Parquet output includes player_id, game_id, season, stat_type, line_value, hit, predicted_proba, fold | PASSED |
| All 4 TEST requirements covered | PASSED |

## Next Phase Readiness

- Phase 5 API can now consume JSON output from the back-test pipeline for serving back-test results
- `backtest_cli.py` is complete and ready for integration with the Phase 5 API layer
- All Phase 4 requirements (TEST-01 through TEST-04) are satisfied by the complete back-testing engine

---
*Phase: 04-back-testing-engine*
*Completed: 2026-04-18*
