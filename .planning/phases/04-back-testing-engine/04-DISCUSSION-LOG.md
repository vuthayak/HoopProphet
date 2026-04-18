# Phase 4: Back-Testing Engine - Discussion Log

> **Audit trail only.** Decisions captured in 04-CONTEXT.md.

**Date:** 2026-04-17
**Phase:** 04-back-testing-engine
**Mode:** discuss

## Gray Areas Identified

1. Backtest output format
2. ROI & vig methodology
3. Calibration curve granularity
4. Reporting depth & validation approach
5. CLI design

## Discussion

### Backtest Output Format
- **Question:** How should back-test results be output?
- **Options presented:** JSON metrics file + console summary / JSON + Parquet per-prediction file / Console-first, JSON on request
- **User chose:** JSON + Parquet per-prediction file
- **Rationale:** JSON for machine consumption (Phase 5 API), Parquet for ad-hoc pandas/notebook analysis

### ROI & Vig Methodology
- **Question:** For vig-adjusted ROI, how should we handle the sportsbook edge?
- **Options presented:** Standard -110 vig only / Configurable vig levels / Accuracy only, defer ROI
- **User chose:** Standard -110 vig only (52.4% breakeven)
- **Rationale:** Common, widely understood, simple to implement. Advanced vig structures can be added later.

### Calibration Curve Granularity
- **Question:** How granular should calibration curves be?
- **Options presented:** Overall + per-stat-type / Overall + per-stat + per-season / Overall only
- **User chose:** Overall + per-stat-type
- **Rationale:** Per-stat reveals which props are better calibrated — critical for betting decisions. Per-season is deferred (thin slices).

### Reporting Depth
- **Question:** What level of detail should the back-test report include?
- **Options presented:** Full report with summaries / Minimal summary only / Full + per-player analysis
- **User chose:** Full report with summaries
- **Rationale:** Enough detail to evaluate trustworthiness without drowning in data.

### Validation Approach
- **Question:** Should the backtest produce a pass/fail verdict, or just report metrics for human review?
- **Options presented:** Report-only (no pass/fail threshold) / Pass/fail thresholds / Report with confidence intervals
- **User chose:** Report with confidence intervals
- **Rationale:** Confidence intervals let a human interpret whether ROI/accuracy is signal or noise, without arbitrary hardcoded thresholds.

### CLI Design
- **Question:** How should the backtest CLI be structured relative to Phase 3's train_cli.py?
- **Options presented:** Follow train_cli pattern (recommended) / Separate CLI script
- **User chose:** Follow train_cli pattern
- **Rationale:** Consistent UX — same `--parquet-path`, `--output-path`, `-v` pattern. Add `--backtest` flag mirroring `--train`.

## Prior Decisions Applied

- Walk-forward temporal splits (not random CV) — locked in Phase 3
- Isotonic preferred, Platt fallback — locked in Phase 3
- Single .joblib artifact — locked in Phase 3
- Offline CLI pipeline pattern — locked in Phase 3
- Long-format Parquet with `hit` target — locked in Phase 2

---

*Phase: 04-back-testing-engine*
*Discussion logged: 2026-04-17*