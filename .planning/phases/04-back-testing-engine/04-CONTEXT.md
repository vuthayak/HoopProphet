# Phase 4: Back-Testing Engine - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Walk-forward back-test evaluation of the trained LightGBM classifier against held-out historical seasons. Produces calibration curves, season-by-season accuracy breakdowns, vig-adjusted ROI metrics, and confidence intervals — so bettors can trust the model's probability predictions before deploying. Stage is validation/reporting only — no model retraining, no API serving, no UI.

</domain>

<decisions>
## Implementation Decisions

### Output format
- **D-01:** Back-test produces two outputs: (1) a JSON metrics file with structured results (fold metrics, season breakdowns, calibration data, ROI), and (2) a Parquet file with per-prediction rows so results can be loaded into pandas/notebooks for ad-hoc analysis. JSON serves API consumption (Phase 5), Parquet serves manual analysis.

### ROI & vig methodology
- **D-02:** Use standard -110 vig (52.4% breakeven threshold) for ROI calculation. This is the most common sportsbook vig structure. ROI is computed as: if the model predicts >52.4% probability and the bet wins at -110 odds, what's the net return? Simple and widely understood.

### Calibration curve granularity
- **D-03:** Produce calibration curves at two levels: overall (all predictions pooled) and per-stat-type (pts, reb, ast, etc.). Per-stat splits let you identify which props the model calibrates better on — critical for deciding which bets to trust. Per-season calibration is deferred (thin slices early on).

### Reporting depth
- **D-04:** Full report with summaries: season-by-season accuracy, overall summary statistics, calibration curves per stat type, and ROI calculation. Enough to evaluate trustworthiness without drowning in data. Per-player breakdowns are out of scope.

### Validation approach
- **D-05:** Report metrics with confidence intervals — no hard pass/fail threshold. The backtest provides statistical evidence (e.g., ROI ± margin, Brier score CI) so a human can interpret whether the model is trustworthy given the sample sizes and variance. Don't bake in arbitrary thresholds.

### CLI design
- **D-06:** Follow the train_cli.py pattern from Phase 3. Same `--parquet-path` for data, `--output-path` for JSON output, `-v` for verbose logging. Add `--backtest` flag to invoke the back-test pipeline (mirrors `--train`). Consistent UX with the existing training CLI.

### the agent's Discretion
- Exact confidence interval method (bootstrap, normal approximation, or Wilson score intervals)
- Number of calibration bins for curves (10 is standard but planner can research)
- Parquet schema for per-prediction output (columns, dtypes)
- How to handle thin-season predictions in per-season breakdowns (merge or flag)
- Whether per-fold metrics reuse Phase 3's `compute_fold_metrics` or the backtest defines its own

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — TEST-01 through TEST-04 (walk-forward back-test, calibration curves, season-by-season accuracy, vig-adjusted ROI)
- `.planning/ROADMAP.md` — Phase 4 goal and success criteria
- `.planning/PROJECT.md` — Probability-based predictions, bettor-relevant metrics

### Phase 3 output (model artifact to backtest)
- `server/pipeline/train_config.py` — `LGBM_PARAMS`, `MODEL_ARTIFACT_PATH`, feature/target column contracts, calibration thresholds
- `server/pipeline/dataset.py` — `load_training_data`, `get_feature_columns`, `prepare_datasets`
- `server/pipeline/splits.py` — `walk_forward_split`, `get_seasons_sorted` (reuse for backtest)
- `server/pipeline/train.py` — `train_model` (for retraining per fold)
- `server/pipeline/calibrate.py` — `calibrate_model` (for re-calibration per fold)
- `server/pipeline/artifact.py` — `save_artifact`, `load_artifact`, `predict_proba`
- `server/pipeline/metrics.py` — `compute_fold_metrics`, `compute_calibration_curve` (extend or reuse)
- `server/pipeline/train_cli.py` — CLI pattern to follow

### Phase 3 context (decisions locked)
- `.planning/phases/03-model-training-calibration/03-CONTEXT.md` — Isotonic preferred with Platt fallback, walk-forward temporal splits, single .joblib artifact

### Research docs (if present)
- `.planning/research/PITFALLS.md` — Random splits, leakage, drift (backtest must avoid these)
- `.planning/research/STACK.md` — Python ML stack expectations

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/pipeline/splits.py` — `walk_forward_split` and `get_seasons_sorted`: backtest reuses the same walk-forward logic as training, but evaluates each fold's predictions instead of training a model
- `server/pipeline/dataset.py` — `load_training_data` and `get_feature_columns`: same data loading pipeline, same feature exclusion rules
- `server/pipeline/calibrate.py` — `calibrate_model` with isotonic/Platt fallback: backtest should re calibrate per fold to match production conditions
- `server/pipeline/metrics.py` — `compute_fold_metrics` and `compute_calibration_curve`: backtest extends these with ROI and confidence interval computation
- `server/pipeline/artifact.py` — `load_artifact` and `predict_proba`: production artifact loading for evaluating saved models
- `server/pipeline/train_config.py` — Configuration constants, paths, and column contracts

### Established Patterns
- Offline pipeline under `server/pipeline/`, tests under `server/tests/`
- CLI pattern: `python -m server.pipeline.train_cli --train` with argparse, `logging.basicConfig`, `sys.exit` codes
- JSON metrics output with `save_metrics_log` pattern from Phase 3
- Walk-forward expanding window across seasons for temporal integrity

### Integration Points
- Backtest reads the same Parquet data (`features.parquet` from Phase 2) that training uses
- Backtest reuses `walk_forward_split` for fold generation — same temporal boundaries as training
- Backtest produces JSON output consumable by Phase 5 API
- Backtest Parquet output enables Phase 7 frontend visualization (future)

</code_context>

<specifics>
## Specific Ideas

- Standard -110 vig is the most common and clearest structure for bettors to understand
- Per-stat-type calibration reveals which props the model handles best — essential for deciding which bets to actually take
- Confidence intervals around ROI help interpret whether positive ROI is real signal or noise (small sample seasons can look great by luck)
- Parquet per-prediction output lets you do ad-hoc pandas analysis — e.g., "how does the model do on props where it's 60-70% confident?"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 4 scope.

</deferred>

---

*Phase: 04-back-testing-engine*
*Context gathered: 2026-04-17*