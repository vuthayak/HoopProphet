# Stack Research: NBA Prop Betting Analytics

**Research Date:** 2025-03-22
**Dimension:** Technology Stack (V2 additions only)

## Executive Summary

V2 transforms HoopProphet from a raw-stat predictor into a probability-based prop betting platform. The existing React + FastAPI + Docker stack remains. This research covers new technology needed for: unified ML classification, feature engineering, offline training, back-testing, and news keyword search.

## ML Model & Training

### LightGBM (Recommended)

**Library:** `lightgbm` (latest stable)
**Confidence:** High

**Why LightGBM over alternatives:**
- **vs XGBoost:** Faster training (histogram-based), native categorical feature support, better with high-cardinality features (player IDs, team matchups). Comparable accuracy on tabular data.
- **vs Random Forest:** LightGBM handles feature interactions and non-linear relationships better; outputs calibrated probabilities with `objective='binary'`.
- **vs Neural Networks:** Tabular sports data with <1M rows is LightGBM's sweet spot. NNs need more data and tuning for marginal gains.
- **vs Logistic Regression:** Too simple for the feature interactions that matter (player × opponent × rest days × home/away).

**Configuration for prop probability:**
- `objective='binary'` (binary classification: over/under)
- `metric='binary_logloss'` (optimizes probability calibration)
- `is_unbalance=False` (props are roughly 50/50 by design)
- Use `predict_proba` for probability output

**Why NOT:**
- Don't use `CatBoost` — slower, marginal accuracy difference, less community tooling for sports analytics.
- Don't use deep learning (PyTorch/TensorFlow) — overkill for this data size, harder to debug, slower iteration.

### Probability Calibration

**Library:** `scikit-learn` `CalibratedClassifierCV`
**Confidence:** High

Use isotonic regression calibration on a held-out validation set. LightGBM's raw probabilities tend to be overconfident on sports data. Calibration ensures that when the model says "75% chance to hit over," it actually hits ~75% historically.

### Model Serialization

**Library:** `joblib` (built into scikit-learn ecosystem)
**Confidence:** High

Save trained LightGBM model + calibrator as a single artifact. Load at API startup for fast inference. Alternatives: `pickle` (security concerns), ONNX (overhead not worth it for this scale).

## Feature Engineering

### Core Feature Pipeline

**Library:** `pandas` + `numpy` (already in stack)
**Confidence:** High

Feature engineering for sports prop prediction is primarily DataFrame operations:
- Rolling window calculations (L5, L10, L20 averages/std)
- Opponent defensive aggregations
- Rest day calculations
- Home/away encoding
- Player consistency metrics (coefficient of variation)

No need for specialized feature stores (Feast, Tecton) at this scale. A well-organized Python module with pandas is sufficient.

### NBA Data Enrichment

**Library:** `nba_api` (already in stack)
**Confidence:** Medium — API is unofficial and rate-limited

Additional endpoints needed for V2 features:
- `LeagueDashTeamStats` — team defensive ratings
- `TeamGameLog` — team pace and tempo data
- `PlayerGameLog` — multi-season game logs (expand beyond current/previous season)
- `CommonPlayerInfo` — player position, height, draft year (for player encoding features)

**Rate limiting strategy:** Cache aggressively. NBA API data changes once daily (after games). Cache with 24-hour TTL for static data, 12-hour for game-day data.

### Data Caching

**Library:** `sqlite3` (Python stdlib) or flat Parquet files via `pyarrow`
**Confidence:** High

Store fetched NBA data locally to avoid re-fetching. Options:
- **SQLite** — simple, relational queries, good for game logs and player data
- **Parquet files** — faster for pandas bulk reads, good for training data snapshots

Recommend: SQLite for raw NBA API caches, Parquet for training-ready feature matrices.

## Back-Testing

### Framework

**Library:** Custom implementation using `scikit-learn` `TimeSeriesSplit` + LightGBM
**Confidence:** High

Sports back-testing requires temporal splits (can't use random k-fold — causes data leakage). The approach:
1. Train on seasons 1..N-1
2. Test on season N
3. Walk forward: train on 1..N, test on N+1
4. Report calibration curves and profit/loss metrics per window

**Key metric:** Calibration plot (reliability diagram) — more important than AUC or accuracy for betting.

No existing sports back-testing framework is worth adopting. Custom implementation (~200-300 lines) is cleaner and more controllable.

## News / Keyword Search

### Approach

**Library:** `requests` + news API (e.g., NewsAPI.org free tier, or Google News RSS)
**Confidence:** Medium

For keyword-based injury/arrest/trade flagging:
- Search `"{player_name}" AND ("injury" OR "out" OR "arrest" OR "trade" OR "questionable" OR "doubtful")`
- Parse results for recency (last 48 hours)
- Flag player with alert type and source

**Alternatives considered:**
- **Full NLP (spaCy, transformers):** Overkill for keyword flagging. Deferred per PROJECT.md.
- **Twitter/X API:** Expensive, rate-limited, unreliable for structured info.
- **ESPN injury reports via web scraping:** Fragile but high-signal. Consider as supplementary source.

## Offline Training Pipeline

### Scheduler

**Approach:** Script-based (`cron` or manual trigger), not a full orchestrator
**Confidence:** High

At this scale, a Python script that:
1. Fetches latest game data from NBA API
2. Builds/updates the feature matrix
3. Retrains LightGBM model
4. Calibrates probabilities
5. Saves model artifact
6. Logs metrics

Run nightly via `cron`, Docker entrypoint script, or manual `python train.py`. No need for Airflow, Prefect, or Dagster — those are for multi-team data platform scale.

### Model Artifact Storage

**Approach:** Local filesystem (`.models/` directory)
**Confidence:** High

Store model artifacts with timestamp: `model_20250322.joblib`. The API loads the latest artifact on startup. Simple, no cloud infrastructure needed.

## Frontend Additions

### Data Visualization

**Library:** Continue with MUI (already in stack) + add `recharts` or `nivo`
**Confidence:** High

For hit rate bars, probability displays, and trend charts:
- **Recharts:** Lightweight, React-native, good for bar charts and line charts. Most popular React charting library.
- **Nivo:** More opinionated, beautiful defaults, but heavier.

Recommend: `recharts` — simpler API, lighter bundle, covers all needed chart types.

### Slider Component

MUI already has `Slider` component for the adjustable stat line feature. No additional library needed.

## Summary

| Category | Recommendation | Rationale |
|----------|---------------|-----------|
| ML Model | LightGBM (binary classification) | Best for tabular sports data, fast, native categoricals |
| Calibration | scikit-learn CalibratedClassifierCV | Ensures trustworthy probabilities |
| Serialization | joblib | Simple, fast, ecosystem standard |
| Feature Engineering | pandas + numpy | Already in stack, sufficient at this scale |
| Data Cache | SQLite + Parquet | SQLite for API cache, Parquet for training data |
| Back-Testing | Custom TimeSeriesSplit | Sports data requires temporal splits |
| News Search | NewsAPI or RSS + keyword matching | Simple, effective for flagging |
| Training Pipeline | Python script + cron | No orchestrator needed at this scale |
| Charts | recharts | Lightweight, React-native, covers all chart types |

---
*Stack research: 2025-03-22*
