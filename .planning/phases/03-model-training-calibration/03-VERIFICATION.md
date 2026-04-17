---
phase: 03-model-training-calibration
verified: 2026-04-17T21:15:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 3: Model Training & Calibration Verification Report

**Phase Goal:** A single unified model produces trustworthy probability predictions for any player prop
**Verified:** 2026-04-17T21:15:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One LightGBM classifier is trained across all players and prop types, outputting probabilities | ✓ VERIFIED | `train.py` uses `LGBMClassifier` with `objective='binary'`, unified across all stat types via `stat_type` categorical feature; dataset loader includes all data without per-player/per-stat filtering |
| 2 | Predicted probabilities are calibrated via isotonic regression so "70% predicted" means ~70% observed hit rate | ✓ VERIFIED | `calibrate.py` uses `CalibratedClassifierCV(cv='prefit', method='isotonic')` when data ≥ 1000 samples with balanced classes; Platt sigmoid fallback when insufficient; calibration curve computation in `metrics.py` provides predicted vs observed data |
| 3 | Model is trained using temporal walk-forward splits, not random cross-validation | ✓ VERIFIED | `splits.py` `walk_forward_split()` uses expanding window on season boundaries; grep confirms no `random`/`KFold`/sklearn.model_selection usage; tests verify no temporal or row leakage |
| 4 | Trained model + calibrator are saved as a single artifact loadable at serving time | ✓ VERIFIED | `artifact.py` `save_artifact()` bundles model+calibrator+feature_columns+metadata into single `.joblib` file; `load_artifact()` retrieves it; `predict_proba()` serves calibrated predictions from loaded artifact |
| 5 | Training is runnable offline as a standalone script with logged metrics (log loss, Brier score) | ✓ VERIFIED | `train_cli.py` enables `python -m server.pipeline.train_cli --train`; `compute_fold_metrics()` logs log_loss, brier_score, accuracy per fold; `compute_calibration_curve()` provides ECE; `save_metrics_log()` writes JSON |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/pipeline/train_config.py` | Training constants — model hyperparameters, paths, feature exclusion, calibration thresholds | ✓ VERIFIED | 63 lines; LGBM_PARAMS with `objective='binary'`, LEAKAGE_COLUMNS, CALIBRATION_MIN_SAMPLES=1000, MODEL_ARTIFACT_PATH, METRICS_LOG_DIR |
| `server/pipeline/dataset.py` | Parquet loading, feature column selection, X/y split with dtype conversion | ✓ VERIFIED | 71 lines; exports `load_training_data`, `get_feature_columns`, `prepare_datasets`, `get_target_column`; excludes ID/TARGET/META/LEAKAGE columns |
| `server/pipeline/splits.py` | Walk-forward temporal split generation | ✓ VERIFIED | 64 lines; exports `walk_forward_split`, `get_seasons_sorted`; no random shuffling; expanding window on season boundaries |
| `server/pipeline/train.py` | LightGBM binary classifier training with early stopping | ✓ VERIFIED | 100 lines; exports `train_model`; returns `(LGBMClassifier, metrics_dict)`; uses early_stopping callback API |
| `server/pipeline/calibrate.py` | Isotonic/Platt calibration with reliability check | ✓ VERIFIED | 133 lines; exports `calibrate_model`, `_check_isotonic_reliability`; cv='prefit' on held-out data; logs method and Brier scores |
| `server/pipeline/artifact.py` | Save/load model artifact as single .joblib with metadata | ✓ VERIFIED | 99 lines; exports `save_artifact`, `load_artifact`, `predict_proba`; bundles model+calibrator+feature_columns+metadata |
| `server/pipeline/metrics.py` | Compute/log metrics: log loss, Brier score, calibration curve | ✓ VERIFIED | 180 lines; exports `compute_fold_metrics`, `compute_calibration_curve`, `save_metrics_log`; computes ECE; writes JSON log |
| `server/pipeline/train_cli.py` | Standalone CLI script for offline training | ✓ VERIFIED | 240 lines; argparse with `--train` flag; orchestrates full pipeline; writes artifact and metrics log |
| `server/requirements.txt` | LightGBM and joblib dependencies | ✓ VERIFIED | Contains `lightgbm>=4.6.0` and `joblib>=1.5.0` |
| `server/tests/test_dataset.py` | Tests for dataset loading and feature exclusion | ✓ VERIFIED | 63 lines; 5 tests covering load, leakage exclusion, model input inclusion, shapes/dtypes, target column |
| `server/tests/test_splits.py` | Tests for walk-forward temporal integrity | ✓ VERIFIED | 77 lines; 6 tests covering chronological sort, fold count, no temporal leakage, no row leakage, insufficient seasons, expanding window |
| `server/tests/test_train.py` | Tests for LightGBM training | ✓ VERIFIED | 79 lines; 5 tests covering classifier type, probability range, categorical features, metrics, feature importances |
| `server/tests/test_calibrate.py` | Tests for calibration with isotonic and Platt fallback | ✓ VERIFIED | 118 lines; 6 tests covering isotonic with sufficient data, Platt fallback, probability range, info logging, reliability check, Brier score |
| `server/tests/test_train_calibrate_integration.py` | End-to-end train+calibrate integration | ✓ VERIFIED | 76 lines; 4 tests covering valid probabilities, method logging, metrics finiteness, full pipeline |
| `server/tests/test_artifact.py` | Tests for artifact save/load round-trip | ✓ VERIFIED | 109 lines; 3 tests covering round-trip, predict_proba, metadata structure |
| `server/tests/test_metrics.py` | Tests for metrics computation | ✓ VERIFIED | 85 lines; 3 tests covering fold metrics, calibration curve with ECE, metrics log save |
| `server/tests/test_train_cli.py` | Integration tests for CLI training pipeline | ✓ VERIFIED | 105 lines; 3 tests covering full pipeline, calibration method recording, MODL-07 field validation |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `dataset.py` | `feature_config.py` | `from server.pipeline.feature_config import STAT_COLS, COMBO_STATS, ALL_TARGET_STATS, STAT_TYPE_MAP, PARQUET_PATH` | ✓ WIRED | Imports confirmed; PARQUET_PATH used in load_training_data, STAT_COLS/COMBO_STATS used for LEAKAGE_COLUMNS |
| `dataset.py` | `train_config.py` | `from server.pipeline.train_config import ID_COLUMNS, TARGET_COLUMNS, META_COLUMNS, LEAKAGE_COLUMNS, CATEGORICAL_FEATURES` | ✓ WIRED | Used in `get_feature_columns()` exclusion logic |
| `train.py` | `train_config.py` | `from server.pipeline.train_config import LGBM_PARAMS, CATEGORICAL_FEATURES, EARLY_STOPPING_ROUNDS` | ✓ WIRED | LGBM_PARAMS control model config, CATEGORICAL_FEATURES used for dtype conversion |
| `train.py` | `dataset.py` | `from server.pipeline.dataset import prepare_datasets` | ✓ WIRED | Called in train_model() to prepare X/y |
| `calibrate.py` | `train_config.py` | `from server.pipeline.train_config import CALIBRATION_METHOD_PREFERRED, CALIBRATION_METHOD_FALLBACK, CALIBRATION_MIN_SAMPLES, CALIBRATION_MIN_PER_BIN` | ✓ WIRED | Used in `_check_isotonic_reliability()` and `calibrate_model()` |
| `calibrate.py` | `sklearn.calibration` | `CalibratedClassifierCV(cv='prefit', method=method)` | ✓ WIRED | Isotonic/sigmoid calibration on held-out data |
| `train_cli.py` | `dataset.py` | `load_training_data, get_feature_columns, prepare_datasets` | ✓ WIRED | Called in pipeline for data loading and feature prep |
| `train_cli.py` | `splits.py` | `walk_forward_split, get_seasons_sorted` | ✓ WIRED | Called for temporal splitting |
| `train_cli.py` | `train.py` | `train_model` | ✓ WIRED | Called per fold and for final model |
| `train_cli.py` | `calibrate.py` | `calibrate_model` | ✓ WIRED | Called on validation/calibration data |
| `train_cli.py` | `artifact.py` | `save_artifact` | ✓ WIRED | Saves final model bundle |
| `train_cli.py` | `metrics.py` | `compute_fold_metrics, compute_calibration_curve, save_metrics_log` | ✓ WIRED | Called to compute and persist metrics |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `dataset.py` → `load_training_data` | `df` (DataFrame) | Phase 2 Parquet file | ✓ Parquet contains real features from feature engineering pipeline | ✓ FLOWING |
| `splits.py` → `walk_forward_split` | `folds` list | DataFrame with season column | ✓ Real season-based temporal boundaries | ✓ FLOWING |
| `train.py` → `train_model` | `model` (LGBMClassifier) | DataFrame → prepare_datasets → X_train, y_train | ✓ Real LightGBM model with learned parameters | ✓ FLOWING |
| `calibrate.py` → `calibrate_model` | `calibrated` (CalibratedClassifierCV) | Fitted model + X_cal, y_cal | ✓ Real calibrated probabilities | ✓ FLOWING |
| `artifact.py` → `save_artifact` | `.joblib` file | model + calibrator + feature_columns + metrics | ✓ Real artifact persistable and loadable | ✓ FLOWING |
| `metrics.py` → `compute_fold_metrics` | metrics dict | y_true, y_pred from calibrated model | ✓ Real log_loss, brier_score, accuracy, calibration_method | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Tests pass | `python -m pytest server/tests/test_dataset.py server/tests/test_splits.py server/tests/test_train.py server/tests/test_calibrate.py server/tests/test_train_calibrate_integration.py server/tests/test_artifact.py server/tests/test_metrics.py server/tests/test_train_cli.py -v --timeout=120` | 35 passed, 25 warnings (all non-blocking deprecation warnings) | ✓ PASS |
| LGBM_PARAMS binary objective | `python -c "from server.pipeline.train_config import LGBM_PARAMS; assert LGBM_PARAMS['objective']=='binary'"` | No error | ✓ PASS |
| Isotonic reliability check | `python -c "from server.pipeline.calibrate import _check_isotonic_reliability; import numpy as np; ok,_=...(np.array([0]*500+[1]*500),1000); assert ok"` | No error | ✓ PASS |
| All module imports | Python import check for all key modules | All imports succeed | ✓ PASS |
| CLI help | `python -m server.pipeline.train_cli --help` | Shows argparse help with --train, --parquet-path, --output-path, --min-train-seasons flags | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MODL-01 | 03-02 | Single unified LightGBM classifier trained across all players and all prop stat types | ✓ SATISFIED | `train_model()` creates one LGBMClassifier; `stat_type` is a categorical feature; all data processed unifyingly |
| MODL-02 | 03-02 | Model uses `objective='binary'` and outputs calibrated probabilities | ✓ SATISFIED | `LGBM_PARAMS['objective'] = 'binary'` in train_config.py; `model.predict_proba()` outputs [0,1] probabilities verified in tests |
| MODL-03 | 03-02 | Isotonic regression calibration via CalibratedClassifierCV on held-out validation set | ✓ SATISFIED | `calibrate.py` uses `CalibratedClassifierCV(estimator=model, method='isotonic', cv='prefit')` when data is sufficient; tests confirm |
| MODL-04 | 03-01 | Model trained using temporal walk-forward split (not random k-fold) | ✓ SATISFIED | `splits.py` uses season-based expanding window; verified no random/KFold; tests confirm no temporal or row leakage |
| MODL-05 | 03-03 | Trained model + calibrator saved as single `.joblib` artifact | ✓ SATISFIED | `artifact.py` bundles model + calibrator + metadata into single joblib file; `load_artifact()` retrieves it; `predict_proba()` serves from it |
| MODL-06 | 03-03 | Training script runnable offline | ✓ SATISFIED | `train_cli.py` works with `python -m server.pipeline.train_cli --train`; argparse CLI with logging and error handling |
| MODL-07 | 03-03 | Training logs metrics: log loss, Brier score, calibration curve data | ✓ SATISFIED | `metrics.py` computes log_loss, brier_score_loss, accuracy, ECE; `save_metrics_log()` writes JSON; per-fold metrics tracked in train_cli.py |

No orphaned requirements — all 7 MODL requirements are covered by plans and verified in code.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `artifact.py` | 47 | `datetime.utcnow()` deprecation | ℹ️ Info | Non-blocking; `datetime.now(datetime.UTC)` recommended for future |
| `calibrate.py` | — | `cv='prefit'` deprecation warning | ℹ️ Info | sklearn 1.6 warns; migration to FrozenEstimator needed in sklearn 1.8 |

No blocker or warning-level anti-patterns found. No TODO/FIXME/placeholder comments. No stub implementations. No empty returns. All functions contain substantive logic.

### Human Verification Required

None. All success criteria are programmatically verifiable:
- Model produces probabilities in [0,1]: tested with assertions
- Calibration method selection: tested with unit tests
- Walk-forward temporal integrity: tested with no-leakage assertions
- Artifact save/load: tested with round-trip tests
- CLI runnable: verified with `--help` and full pipeline test

### Gaps Summary

No gaps found. All 5 success criteria are verified:
1. ✓ Single unified LightGBM classifier with binary objective
2. ✓ Isotonic calibration with Platt fallback (<1000 samples threshold)
3. ✓ Temporal walk-forward splits (no random shuffling)
4. ✓ Single .joblib artifact with model+calibrator+metadata
5. ✓ Standalone CLI with logged metrics (log loss, Brier score, calibration curve)

All 7 MODL requirements (MODL-01 through MODL-07) are satisfied. All 35 tests pass. No anti-patterns, stubs, or wiring gaps found.

---

_Verified: 2026-04-17T21:15:00Z_
_Verifier: the agent (gsd-verifier)_