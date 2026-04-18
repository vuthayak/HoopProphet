---
status: complete
phase: 04-back-testing-engine
source:
  - .planning/phases/04-back-testing-engine/04-01-SUMMARY.md
  - .planning/phases/04-back-testing-engine/04-02-SUMMARY.md
  - .planning/phases/04-back-testing-engine/04-03-SUMMARY.md
started: 2026-04-18T05:52:00Z
updated: 2026-04-18T05:59:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Running `python -m server.pipeline.backtest_cli --help` starts without errors and displays CLI help with --backtest, --parquet-path, --output-path, -v arguments.
result: pass

### 2. CLI Help Output
expected: Help shows --backtest flag, --parquet-path, --output-path, --min-train-seasons, --output-dir, -v arguments
result: pass

### 3. End-to-End Pipeline with Synthetic Data
expected: `python -m server.pipeline.backtest_cli --backtest` runs successfully using synthetic training data and produces JSON + Parquet output files in BACKTEST_METRICS_DIR
result: issue
reported: "ValueError: Need at least 3 seasons for walk-forward back-test, got 0 ([])"
severity: major

### 4. JSON Output Structure
expected: JSON output contains all required sections: backtest_metadata (n_folds, seasons, breakeven_threshold), fold_metrics, season_breakdown, overall_calibration, per_stat_calibration, roi, confidence_intervals
result: blocked
blocked_by: prior-phase
reason: "Pipeline fails before producing output - depends on fixing Test 3"

### 5. Parquet Output Columns
expected: Parquet file contains per-prediction rows with columns: player_id, game_id, season, stat_type, line_value, hit, predicted_proba, fold
result: blocked
blocked_by: prior-phase
reason: "Pipeline fails before producing output - depends on fixing Test 3"

### 6. Calibration Curves Computed
expected: compute_overall_calibration and compute_per_stat_calibration return valid calibration curve data (fraction_positives, mean_predicted_value, bin_counts, ece)
result: pass

### 7. Vig-Adjusted ROI
expected: ROI metrics use -110 vig (0.909 profit per win, -1.0 per loss) at 52.4% breakeven threshold
result: pass

### 8. Bootstrap Confidence Intervals
expected: compute_confidence_intervals returns dict with low/mid/high keys for accuracy, brier_score, log_loss, roi metrics
result: pass

## Summary

total: 8
passed: 5
issues: 1
pending: 0
skipped: 0
blocked: 2

## Gaps

- truth: "CLI runs end-to-end with synthetic or default data and produces JSON + Parquet output"
  status: failed
  reason: "User reported: ValueError: Need at least 3 seasons for walk-forward back-test, got 0 ([])"
  severity: major
  test: 3
  root_cause: "server/data/features.parquet exists but is empty (0 rows, 0 seasons). When --parquet-path is not provided, backtest_cli falls back to PARQUET_PATH which points to this empty file."
  artifacts:
    - path: "server/pipeline/backtest_cli.py"
      issue: "No graceful handling when default parquet is empty or missing seasons"
    - path: "server/data/features.parquet"
      issue: "File exists but has 0 data rows"
  missing:
    - "Either: create non-empty features.parquet with real/synthetic season data, OR add synthetic data fallback to CLI, OR detect empty parquet early and provide helpful error"
