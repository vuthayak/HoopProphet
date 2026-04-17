---
phase: 03-model-training-calibration
plan: 01
subsystem: ml-training
tags: [lightgbm, joblib, walk-forward, temporal-split, dataset-loader, calibration, binary-classification]

# Dependency graph
requires:
  - phase: 02-feature-engineering-pipeline
    provides: Long-format Parquet with features and binary targets (features.parquet)
provides:
  - Training config module (train_config.py) with hyperparameters, feature exclusion, calibration thresholds
  - Dataset loader (dataset.py) that reads Parquet and produces X/y with proper dtype conversion
  - Walk-forward temporal split generator (splits.py) with expanding window
  - Synthetic training Parquet test fixture in conftest.py
affects: [03-model-training-calibration, 04-back-testing]

# Tech tracking
tech-stack:
  added: [lightgbm>=4.6.0, joblib>=1.5.0]
  patterns: [walk-forward-validation, feature-exclusion-leakage-guard, expanding-window-temporal-split]

key-files:
  created:
    - server/pipeline/train_config.py
    - server/pipeline/dataset.py
    - server/pipeline/splits.py
    - server/tests/test_dataset.py
    - server/tests/test_splits.py
  modified:
    - server/requirements.txt
    - server/tests/conftest.py

key-decisions:
  - "LightGBM binary classification with min_child_samples=50 to prevent overfitting per PITFALLS"
  - "Isotonic regression preferred for calibration, Platt sigmoid fallback when < 1000 samples"
  - "Season boundaries as natural temporal separators — no embargo gap needed"
  - "Optuna hyperparameter tuning deferred to Phase 4 back-test optimization"
  - "Feature exclusion via ID/TARGET/META/LEAKAGE column sets prevents target leakage from raw stats"

patterns-established:
  - "Walk-forward expanding window: train on seasons [1..N], validate on season N+1 — no random splits"
  - "Feature column whitelist: exclude raw stat columns (STAT_COLS) and combo stats (COMBO_STATS) that leak the target"
  - "stat_type as LightGBM categorical feature, numeric columns cast to float32 for efficiency"

requirements-completed: [MODL-04]

# Metrics
duration: 2min
completed: 2026-04-17
---

# Phase 3: Model Training & Calibration Summary

**Training foundation: LightGBM/jolib deps, config module with calibration thresholds, Parquet dataset loader with leakage exclusion, and walk-forward temporal splits**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-17T20:28:25Z
- **Completed:** 2026-04-17T20:30:34Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Added LightGBM and joblib dependencies, verified importability
- Created train_config.py with binary classification hyperparameters, feature exclusion rules (ID, target, meta, leakage columns), calibration config (isotonic preferred, Platt fallback at <1000 samples), and metrics logging paths
- Created dataset.py with load_training_data, get_feature_columns (excludes 16 raw stats + 3 combo stats + IDs + metadata from features), prepare_datasets (stat_type → category, numerics → float32), and get_target_column
- Created splits.py with walk_forward_split (expanding window, temporal ordering, no random shuffle) and get_seasons_sorted
- Added training_parquet pytest fixture with 3 seasons × 2 players × 2 stats of synthetic long-format data
- All 11 unit tests pass: dataset loading, feature exclusion/inclusion, dtype conversion, temporal split integrity, expanding window, insufficient seasons error

## Task Commits

Each task was committed atomically:

1. **Task 1: Dependencies and Training Configuration Module** - `5ac3113` (feat)
2. **Task 2: Dataset Loader and Walk-Forward Split Logic** - `76e16db` (feat)
3. **Task 3: Tests for Dataset Loading and Walk-Forward Splits** - `bfc084f` (test)

## Files Created/Modified
- `server/requirements.txt` - Added lightgbm>=4.6.0 and joblib>=1.5.0
- `server/pipeline/train_config.py` - Training constants: LGBM_PARAMS, feature exclusion rules (ID_COLUMNS, TARGET_COLUMNS, META_COLUMNS, LEAKAGE_COLUMNS), calibration config, walk-forward config, metrics logging
- `server/pipeline/dataset.py` - Parquet loader, feature column selector, X/y preparation with dtype conversion
- `server/pipeline/splits.py` - Walk-forward expanding-window temporal split generator with season boundary enforcement
- `server/tests/conftest.py` - Added training_parquet fixture with synthetic 3-season data
- `server/tests/test_dataset.py` - 5 tests: load, exclude leakage, include model inputs, shapes/dtypes, target column
- `server/tests/test_splits.py` - 6 tests: chronological sort, fold count, no temporal leakage, no row leakage, insufficient seasons, expanding window

## Decisions Made
- Used LightGBM binary objective (not XGBoost) per STACK.md recommendation — faster training on tabular data with native categorical support
- min_child_samples=50 prevents overfitting per PITFALLS.md guidance
- Calibration: isotonic preferred, Platt fallback when sample count < 1000 (per D-01/D-02 in CONTEXT.md)
- Season boundaries serve as natural temporal separators; EMBARGO_GAMES=0 since full seasons are non-overlapping
- Optuna deferred to Phase 4 (not needed for initial training defaults)
- Feature exclusion set combines STAT_COLS (16 raw stats) + COMBO_STATS keys (pra, pa, pr) = 19 leakage columns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Training config, dataset loader, and walk-forward splits are ready for Phase 3 Plan 02 (model training and calibration pipeline)
- The training_parquet fixture provides synthetic data for unit testing; the real features.parquet from Phase 2 will be used in production training
- All imports verified: dataset, splits, train_config modules are importable from server.pipeline

---
*Phase: 03-model-training-calibration*
*Completed: 2026-04-17*