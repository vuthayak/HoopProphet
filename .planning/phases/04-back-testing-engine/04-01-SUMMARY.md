---
phase: 04-back-testing-engine
plan: "01"
subsystem: testing
tags: [lightgbm, backtesting, walk-forward, calibration, sports-betting]

# Dependency graph
requires:
  - phase: 03-model-training-calibration
    provides: walk_forward_split, train_model, calibrate_model, load_training_data
provides:
  - Walk-forward back-test evaluation engine producing per-prediction DataFrames
  - backtest_config.py with vig/breakeven/calibration constants
  - BacktestResult dataclass and run_backtest function
  - 16 unit tests covering all 7 behavior specs
affects:
  - Phase 4 Plan 02 (metrics computation from predictions_df)
  - Phase 4 Plan 03 (CLI output from fold_summaries)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Walk-forward temporal evaluation (train on N-1 seasons, predict on N)
    - Per-fold model retraining and calibration
    - Dataclass-based result aggregation

key-files:
  created:
    - server/pipeline/backtest_config.py
    - server/pipeline/backtest.py
    - server/tests/test_backtest.py
  modified: []

key-decisions:
  - "Used walk_forward_split from Phase 3 directly — no new temporal split logic"
  - "Calibrated model per fold to match production conditions (isotonic with Platt fallback)"
  - "Per-prediction rows include stat_type as integer code per feature_config"

patterns-established:
  - "BacktestResult dataclass aggregates predictions_df + fold_summaries for downstream Plans 02/03"
  - "walk_forward_split + train_model + calibrate_model chain reused without duplication"

requirements-completed:
  - TEST-01

# Metrics
duration: 3min
completed: 2026-04-18
---

# Phase 4 Plan 01: Walk-Forward Back-Test Engine Summary

**Walk-forward back-test evaluation engine using walk_forward_split from Phase 3, producing per-prediction DataFrames across held-out historical season folds**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T05:38:58Z
- **Completed:** 2026-04-18T05:42:00Z
- **Tasks:** 1 (TDD RED→GREEN)
- **Files created:** 3 (backtest_config.py, backtest.py, test_backtest.py)

## Accomplishments
- Walk-forward back-test engine that evaluates LightGBM model across historical season folds
- Per-prediction DataFrame with player_id, game_id, season, stat_type, line_value, hit, predicted_proba, fold columns
- BacktestResult dataclass with predictions_df, fold_summaries, n_folds, seasons
- Reuses Phase 3 walk_forward_split, train_model, calibrate_model — zero duplication
- 16 unit tests covering all 7 behavior specs from the plan

## Task Commits

Each task was committed atomically:

1. **Task 1: Back-test configuration and walk-forward evaluation engine** - `d1f45bd` (feat)

**Plan metadata:** `d1f45bd` (feat: complete plan)

## Files Created/Modified

- `server/pipeline/backtest_config.py` - Configuration constants: BREAKEVEN_THRESHOLD (0.524), VIG_MULTIPLIER (0.909), CALIBRATION_BINS (10), BOOTSTRAP_SAMPLES (1000), MIN_TRAIN_SEASONS (2), BACKTEST_METRICS_DIR, ALL_TARGET_STATS
- `server/pipeline/backtest.py` - BacktestResult dataclass and run_backtest function; imports walk_forward_split, train_model, calibrate_model from Phase 3; per-fold training/calibration/prediction pipeline
- `server/tests/test_backtest.py` - 16 unit tests covering 7 behavior specs: fold count, train/val split correctness, required columns, probability range [0,1], no temporal leakage, ValueError on insufficient seasons, BacktestResult dataclass fields

## Decisions Made

- Used walk_forward_split from Phase 3 directly — no new temporal split logic
- Calibrated model per fold to match production conditions (isotonic with Platt fallback)
- Per-prediction rows include stat_type as integer code per feature_config (stat_type_name mapping deferred to Plan 02)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Verification Results

| Check | Result |
|-------|--------|
| `python -m pytest server/tests/test_backtest.py -x` | PASSED (16/16) |
| `from server.pipeline.backtest import run_backtest, BacktestResult` | PASSED |
| `from server.pipeline.backtest_config import BREAKEVEN_THRESHOLD, VIG_MULTIPLIER, CALIBRATION_BINS, BOOTSTRAP_SAMPLES` | PASSED |
| `BREAKEVEN_THRESHOLD == 0.524` | PASSED |
| backtest.py imports walk_forward_split from splits | PASSED (reuses Phase 3) |
| backtest.py imports train_model and calibrate_model | PASSED (reuses Phase 3) |

## Next Phase Readiness

- Plan 02 (metrics computation) can now use BacktestResult.predictions_df for calibration curves, ROI, and season-by-season breakdowns
- Plan 03 (CLI output) can use BacktestResult.fold_summaries for per-fold reporting
- All Phase 3 artifacts (splits, train, calibrate, dataset) are correctly chained

---
*Phase: 04-back-testing-engine*
*Completed: 2026-04-18*
