---
phase: 03-model-training-calibration
plan: 02
subsystem: ml-training
tags: [lightgbm, binary-classification, calibration, isotonic-regression, platt-scaling, sklearn]

# Dependency graph
requires:
  - phase: 02-feature-engineering-pipeline
    provides: Long-format Parquet with features and binary targets
  - phase: 03-model-training-calibration/03-01
    provides: Training config, dataset loader, walk-forward splits, conftest fixture
provides:
  - LightGBM binary classifier training function (train_model)
  - Isotonic regression calibration with Platt fallback (calibrate_model)
  - Calibration reliability check (_check_isotonic_reliability)
  - Full train-then-calibrate integration tests
affects: [03-model-training-calibration, 04-back-testing]

# Tech tracking
tech-stack:
  added: []
  patterns: [binary-classification-unified-model, isotonic-calibration-with-fallback, early-stopping-callbacks-api, calibration-reliability-gate]

key-files:
  created:
    - server/pipeline/train.py
    - server/pipeline/calibrate.py
    - server/tests/test_train.py
    - server/tests/test_calibrate.py
    - server/tests/test_train_calibrate_integration.py
  modified: []

key-decisions:
  - "Used LightGBM callback API (early_stopping + log_evaluation) instead of deprecated keyword arguments for LightGBM >= 4.0 compatibility"
  - "Changed class imbalance boundary from strict < to <= for CALIBRATION_MIN_PER_BIN — exactly 10 positive samples is unreliable for isotonic"
  - "CalibratedClassifierCV with cv='prefit' for post-hoc calibration on held-out data (sklearn 1.6 deprecation warning noted, will migrate to FrozenEstimator in future)"

patterns-established:
  - "train_model() returns (model, metrics_dict) with log_loss for both train and validation"
  - "calibrate_model() returns (calibrated_model, calibration_info) with method, reason, Brier scores"
  - "Calibration reliability gate: <1000 total samples or <=10 min class samples triggers Platt fallback"

requirements-completed: [MODL-01, MODL-02, MODL-03]

# Metrics
duration: 2min
completed: 2026-04-17
---

# Phase 3 Plan 2: LightGBM Training & Calibration Summary

**Unified LightGBM binary classifier with isotonic regression calibration and Platt sigmoid fallback**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-17T20:31:43Z
- **Completed:** 2026-04-17T20:34:39Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Implemented train_model() for unified LightGBM binary classification across all players and stat types (MODL-01, MODL-02)
- Implemented calibrate_model() with isotonic regression preferred and Platt sigmoid fallback when data is insufficient (MODL-03, D-01/D-02)
- Added calibration reliability gate that logs which method was applied and why
- All 15 tests pass: 5 training + 6 calibration + 4 integration
- Full end-to-end pipeline validated: walk-forward split → train → calibrate → probability predictions

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: LightGBM training tests** - `7843501` (test)
2. **Task 1 GREEN: LightGBM training implementation** - `3355c41` (feat)
3. **Task 2 RED: Isotonic calibration tests** - `f7aa404` (test)
4. **Task 2 GREEN: Isotonic calibration implementation** - `c360b41` (feat)
5. **Task 3: Integration tests** - `536de67` (feat)

## Files Created/Modified
- `server/pipeline/train.py` - LightGBM binary classifier training with early stopping, categorical features, metrics
- `server/pipeline/calibrate.py` - Isotonic regression calibration with Platt fallback, Brier score tracking, reliability check
- `server/tests/test_train.py` - 5 tests: classifier type, probability range, categorical features, metrics, feature importances
- `server/tests/test_calibrate.py` - 6 tests: isotonic with sufficient data, Platt fallback, probability range, info logging, reliability check, Brier score
- `server/tests/test_train_calibrate_integration.py` - 4 tests: valid probabilities, method logging, metrics finiteness, full pipeline

## Decisions Made
- Used LightGBM callback API (early_stopping + log_evaluation) for LightGBM >= 4.0 compatibility instead of deprecated keyword arguments
- Changed class imbalance boundary from strict `<` to `<=` for CALIBRATION_MIN_PER_BIN — exactly N min class samples is still unreliable for isotonic regression
- Kept CalibratedClassifierCV with `cv='prefit'` per plan specification; sklearn 1.6 deprecation warning noted for future migration to FrozenEstimator

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed class imbalance boundary condition in _check_isotonic_reliability**
- **Found during:** Task 2 (Isotonic Calibration with Platt Fallback)
- **Issue:** Test `test_isotonic_reliability_check` failed because the code used strict `<` for `CALIBRATION_MIN_PER_BIN` check, but having exactly 10 positive samples out of 1000 (990/10 split) should still be considered unreliable for isotonic regression
- **Fix:** Changed `min_class_samples < CALIBRATION_MIN_PER_BIN` to `min_class_samples <= CALIBRATION_MIN_PER_BIN` — at the threshold value, class imbalance is still too severe for stable isotonic fitting
- **Files modified:** server/pipeline/calibrate.py
- **Verification:** All 6 calibration tests pass
- **Committed in:** c360b41 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Critical correctness fix — without it, severely imbalanced calibration data would incorrectly use isotonic regression, producing unstable calibration curves. No scope creep.

## Issues Encountered
- sklearn 1.6 deprecation warning for `cv='prefit'` in CalibratedClassifierCV — plan explicitly specifies this API; works correctly but will need migration to FrozenEstimator when sklearn 1.8 removes it

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- train_model() and calibrate_model() are ready for Plan 03 (model packaging and training script)
- The training pipeline can be invoked as: train_model() → calibrate_model() → save artifact (upcoming)
- All imports verified: both modules importable from server.pipeline
- No random k-fold cross-validation anywhere — only walk-forward temporal splits (MODL-04)

## Self-Check: PASSED

- All 5 key files verified FOUND on disk
- 5 commits with `03-02` tag found in git log
- All 15 plan-related tests pass (5 train + 6 calibrate + 4 integration)
- All 4 verification commands pass: imports, binary objective, isotonic check, full test suite
- No untracked task-related files

---
*Phase: 03-model-training-calibration*
*Completed: 2026-04-17*