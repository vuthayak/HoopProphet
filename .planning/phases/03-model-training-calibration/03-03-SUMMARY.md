---
phase: 03-model-training-calibration
plan: 03
subsystem: ml-training
tags: [joblib, artifact, metrics, calibration-curve, brier-score, log-loss, cli, argparse]

# Dependency graph
requires:
  - phase: 03-model-training-calibration/03-02
    provides: train_model(), calibrate_model() with isotonic/sigmoid fallback
  - phase: 03-model-training-calibration/03-01
    provides: Training config, dataset loader, walk-forward splits, conftest fixture
provides:
  - Model artifact save/load via single .joblib bundle (MODL-05)
  - predict_proba() serving interface from loaded artifact
  - Training metrics: log_loss, Brier score, accuracy, calibration curve per fold (MODL-07)
  - Standalone CLI script for offline training (MODL-06)
  - End-to-end integration tests covering full pipeline
affects: [04-back-testing, 05-prop-analysis-api]

# Tech tracking
tech-stack:
  added: []
  patterns: [joblib-artifact-bundle, metrics-json-logging, calibration-curve-ece, cli-pipeline-orchestration]

key-files:
  created:
    - server/pipeline/artifact.py
    - server/pipeline/metrics.py
    - server/pipeline/train_cli.py
    - server/tests/test_artifact.py
    - server/tests/test_metrics.py
    - server/tests/test_train_cli.py
  modified:
    - server/pipeline/metrics.py (ECE computation fix)
    - server/pipeline/train_cli.py (metrics_dir param, accuracy in final fold)

key-decisions:
  - "Aligned calibration_curve ECE computation with sklearn output: handle empty bins by masking, truncate to non-empty bin count"
  - "Added metrics_dir override to run_training_pipeline for test isolation"
  - "Passed calibration_method at top level of metrics dict in save_artifact call for metadata extraction"
  - "Included accuracy field in final fold metrics for complete MODL-07 record"

patterns-established:
  - "Artifact bundle pattern: model + calibrator + feature_columns + metadata as single .joblib"
  - "predict_proba() as serving interface: load artifact once, call per request"
  - "CLI follows ingest.py pattern: argparse, logging.basicConfig, sys.exit codes"
  - "Walk-forward metrics: log_loss + Brier score + accuracy + calibration curve per fold, plus final production model"
  - "ECE (Expected Calibration Error) computed alongside calibration curve for model quality assessment"

requirements-completed: [MODL-05, MODL-06, MODL-07]

# Metrics
duration: 4min
completed: 2026-04-17
---

# Phase 3 Plan 3: Artifact Persistence, Metrics & CLI Summary

**Single .joblib artifact persistence with metadata, walk-forward metrics logging, and CLI training pipeline orchestration**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-17T20:36:36Z
- **Completed:** 2026-04-17T20:40:33Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Created artifact.py with save_artifact/load_artifact/predict_proba for single .joblib model bundle (MODL-05)
- Created metrics.py with compute_fold_metrics, compute_calibration_curve (with ECE), and save_metrics_log (MODL-07)
- Created train_cli.py CLI orchestrating full pipeline: load → walk-forward split → train → calibrate → metrics → save (MODL-06)
- All 9 tests pass: 3 artifact + 3 metrics + 3 end-to-end integration
- CLI produces model artifact with embedded metadata including calibration method

## Task Commits

Each task was committed atomically:

1. **Task 1: Artifact Persistence and Metrics Computation** - `0f74bd2` (feat)
2. **Task 2: CLI Training Script — End-to-End Pipeline Orchestration** - `6a5a37e` (feat)
3. **Task 3: Integration Test — End-to-End Training Pipeline** - `801e07c` (feat)

## Files Created/Modified
- `server/pipeline/artifact.py` - Save/load model artifact as single .joblib with metadata; predict_proba serving interface
- `server/pipeline/metrics.py` - Log loss, Brier score, accuracy per fold; calibration curve with ECE; JSON metrics logging
- `server/pipeline/train_cli.py` - CLI script orchestrating full training pipeline with walk-forward splits and artifact saving
- `server/tests/test_artifact.py` - 3 tests: round-trip save/load, predict_proba probabilities, metadata structure
- `server/tests/test_metrics.py` - 3 tests: fold metrics computation, calibration curve with ECE, metrics log save
- `server/tests/test_train_cli.py` - 3 integration tests: full pipeline, calibration method recording, MODL-07 field validation

## Decisions Made
- Fixed ECE computation in calibration_curve to handle sklearn dropping empty bins (aligned bin counts with fraction_positives array)
- Added `metrics_dir` parameter to `run_training_pipeline()` for test isolation (doesn't pollute project data dirs)
- Passed `calibration_method` at top-level in metrics dict so `save_artifact()` can extract it for artifact metadata
- Included accuracy field in final fold metrics for complete MODL-07 compliance
- Followed ingest.py CLI pattern for train_cli.py: argparse with --train flag, logging.basicConfig, sys.exit codes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ECE computation alignment with sklearn calibration_curve**
- **Found during:** Task 1 (Artifact Persistence and Metrics Computation)
- **Issue:** calibration_curve() can return fewer bins than requested when some are empty, causing a shape mismatch ValueError in ECE computation
- **Fix:** Aligned bin counts by masking non-empty bins and truncating to match calibration_curve output length; added safety min_len check
- **Files modified:** server/pipeline/metrics.py
- **Verification:** All 6 artifact + metrics tests pass
- **Committed in:** 0f74bd2 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test assertion for calibration curve bin count**
- **Found during:** Task 1 (Artifact Persistence and Metrics Computation)
- **Issue:** Test asserted `len(fraction_positives) == 10` but sklearn may return fewer non-empty bins
- **Fix:** Changed assertion to `len(fraction_positives) <= 10` since empty bins are dropped
- **Files modified:** server/tests/test_metrics.py
- **Verification:** All metrics tests pass
- **Committed in:** 0f74bd2 (Task 1 commit)

**3. [Rule 3 - Blocking] Added missing accuracy field to final fold metrics and calibration_method to artifact metadata**
- **Found during:** Task 3 (Integration Tests)
- **Issue:** Final fold metrics dict was missing `accuracy` field causing KeyError in save_metrics_log; `save_artifact` metadata had calibration_method='unknown' because metrics dict didn't have top-level calibration_method key
- **Fix:** Added accuracy field (computed from final model predictions) and n_val field to final fold metrics; added calibration_method at top level of metrics dict passed to save_artifact
- **Files modified:** server/pipeline/train_cli.py
- **Verification:** All 3 integration tests pass, including calibration method verification
- **Committed in:** 801e07c (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All auto-fixes were essential for correctness — ECE computation bug would crash at runtime with real data, test assertion was overly strict, and missing fields would cause runtime KeyErrors. No scope creep.

## Issues Encountered
- sklearn 1.6 deprecation warning for `cv='prefit'` in CalibratedClassifierCV — already noted in Plan 02, not a blocking issue
- `datetime.datetime.utcnow()` deprecation warning — non-blocking, cosmetic

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Model artifact persistence complete (MODL-05), CLI training script operational (MODL-06), metrics logging complete (MODL-07)
- Phase 3 (Model Training & Calibration) is now complete — all 7 MODL requirements satisfied
- Ready for Phase 4 (Back-Testing): the saved artifact can be loaded for walk-forward back-testing evaluation

## Self-Check: PASSED

- All 6 key files exist on disk
- 3 commits with `03-03` tag found in git log
- All 9 plan-related tests pass (3 artifact + 3 metrics + 3 integration)
- All 5 verification commands pass: pytest suite, CLI help, 3 import checks
- No untracked task-related files

---
*Phase: 03-model-training-calibration*
*Completed: 2026-04-17*