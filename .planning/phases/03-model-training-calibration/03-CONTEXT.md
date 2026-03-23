# Phase 3: Model Training & Calibration - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Train a **single unified LightGBM binary classifier** on the Phase 2 long-format Parquet dataset (`hit` vs features), apply **probability calibration** so predicted percentages match observed hit rates, validate with **temporal walk-forward splits** (not random k-fold), and persist **one loadable artifact** (model + calibrator + metadata) for offline runs and later API serving. Scope is training/calibration only — back-test reporting and API integration are later phases.
</domain>

<decisions>
## Implementation Decisions

### Calibration
- **D-01:** Prefer **isotonic regression** for calibration (aligned with MODL-03 / roadmap). When validation data is too sparse for stable isotonic fitting, **automatically fall back to Platt scaling (sigmoid)** on the same held-out calibration split. The training run must **log which method was applied** (e.g. `calibration_method: isotonic` vs `platt`).
- **D-02:** Do **not** fail the pipeline solely because isotonic is unreliable — use the fallback so the phase remains shippable with thin early-season data, while still preferring isotonic when sample size supports it.

### Claude's Discretion
- Exact thresholds for “isotonic unreliable” (min validation rows, per-bin counts, or heuristics) — researcher/planner define from literature + empirical checks.
- Walk-forward fold definitions, season ordering, and embargo rules (MODL-04) — not locked in discuss-phase; must satisfy temporal integrity and no leakage.
- LightGBM hyperparameters, feature list from Parquet (excluding raw stat columns that leak), artifact file layout beyond “single `.joblib`” bundle, CLI flags and log formats (MODL-06/07).
- Whether to expose calibration curve arrays in logs only vs also persist alongside artifact.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — MODL-01 through MODL-07 (unified classifier, binary objective, isotonic/CalibratedClassifierCV, walk-forward split, `.joblib` artifact, offline script, metrics).
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria.
- `.planning/PROJECT.md` — Unified LightGBM, binary framing, offline training.

### Phase 2 output (training data)
- `server/pipeline/feature_config.py` — `PARQUET_PATH`, `STAT_TYPE_MAP`, target stat list, `MIN_GAMES_PER_SEASON`.
- `server/pipeline/features.py` — `run_feature_pipeline` contract and Parquet write.
- `.planning/phases/02-feature-engineering-pipeline/02-CONTEXT.md` — Long-format targets, temporal guards, multi-line thresholds.

### Legacy V1 (replace, do not extend for V2 training)
- `server/ml/model_train.py` — V1 regression + repeated k-fold + Gemini summary; **not** the V2 training path.

### Research docs (if present)
- `.planning/research/PITFALLS.md` — Random splits, leakage, drift.
- `.planning/research/STACK.md` — Python ML stack expectations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- Phase 2 Parquet at `server/data/features.parquet` (path from `feature_config.PARQUET_PATH`) — primary training table.
- `server/pipeline/feature_config.py` — `stat_type` categorical mapping and feature/target column contracts.

### Established patterns
- Offline pipeline under `server/pipeline/`; tests under `server/tests/`.
- Legacy V1 ML under `server/ml/` (pandas, sklearn, XGBoost regression) — **V2 Phase 3 should introduce a new training entrypoint** aligned with MODL-* (LightGBM + calibration + walk-forward), not retrofit `model_train.py`’s regression CV loop.

### Integration points
- Training reads Parquet produced by Phase 2; writes artifact consumed by Phase 5 (API) and evaluated in Phase 4 (backtest).

</code_context>

<specifics>
## Specific Ideas

- User chose **isotonic first, Platt fallback** when isotonic is unreliable — balances strict calibration intent with practical early-season / small-validation windows.
- STATE.md noted a prior concern: isotonic may need **5K+ samples** — fallback path addresses that without blocking the pipeline.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 3 scope.

</deferred>

---

*Phase: 03-model-training-calibration*
*Context gathered: 2026-03-23*
