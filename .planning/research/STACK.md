# Technology Stack — V2 Additions

**Project:** HoopProphet V2 (Probability-Based Prop Betting Analytics)
**Researched:** 2026-03-22
**Scope:** NEW dependencies only — React, FastAPI, Docker Compose, MUI, Emotion, Framer Motion are retained from V1 and not re-evaluated here.

## Recommended Stack

### ML Core — Unified LightGBM Classifier

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| lightgbm | 4.6.0 | Unified binary classifier for over/under prop prediction | Fastest GBDT for tabular data; native categorical support eliminates one-hot encoding of teams/positions; histogram-based splits handle 100K+ training rows efficiently; scikit-learn compatible API simplifies pipeline integration. Outperforms XGBoost on training speed for this data shape (many categorical features, moderate row count). [HIGH confidence — verified via PyPI and official docs] |
| scikit-learn | 1.8.0 | Calibration (`CalibratedClassifierCV`), preprocessing (`StandardScaler`), evaluation (`brier_score_loss`, `log_loss`, `calibration_curve`), train/test splitting | Already in V1 for pipelines; V2 uses it specifically for probability calibration (isotonic regression on held-out validation set) and evaluation metrics. Requires Python ≥3.11. [HIGH confidence — verified via PyPI] |
| optuna | 4.8.0 | Hyperparameter tuning for LightGBM | `optuna-integration` provides `LightGBMTuner` with stepwise tuning of `num_leaves`, `feature_fraction`, `bagging_fraction`, `lambda_l1/l2`, `min_child_samples` — faster than grid/random search. Define-by-run API. [HIGH confidence — verified via PyPI and official docs] |
| optuna-integration | 4.8.0 | LightGBM-specific Optuna integration | Provides `LightGBMTuner` and `LightGBMTunerCV` classes that wrap LightGBM's training API with built-in Optuna optimization. [HIGH confidence — verified via PyPI] |
| shap | 0.51.0 | Model explainability — feature importance for prop predictions | `TreeExplainer` computes SHAP values in linear time for LightGBM trees. Answers "why does the model think this prop hits?" — critical for user trust and debugging. Waterfall/force plots can feed frontend explainability panels later. [HIGH confidence — verified via PyPI] |

### Model Lifecycle — Offline Training & Serving

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| joblib | 1.5.3 | Serialize trained LightGBM pipeline + calibrator to disk | Standard for scikit-learn-compatible model persistence. Save the full pipeline (feature transforms + LightGBM + calibrator) as a single `.joblib` artifact. Faster than pickle for numpy-heavy objects. [HIGH confidence — verified via PyPI] |
| APScheduler | 3.11.1 | Schedule nightly/weekly model retraining | `BackgroundScheduler` or `BlockingScheduler` with cron triggers. Lightweight — no Redis/Celery overhead for a single-container training job. Persists job state to SQLite if needed. [MEDIUM confidence — version verified via PyPI; alternative is plain cron, but APScheduler integrates with Python directly] |

**Model artifact strategy:** Train offline → save `model.joblib` with metadata (training date, feature list, metrics) → FastAPI loads artifact at startup → serve predictions from in-memory model. No per-request training.

### Data Pipeline — Collection & Caching

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| nba_api | 1.11.4 | NBA game logs, player stats, team stats (already in V1) | V2 uses `SeasonAll` parameter for multi-season bulk extraction and `LeagueGameLog` for league-wide data. Migrate from `PlayByPlayV2`→`V3` and `ScoreboardV2`→`V3` (V2 endpoints deprecated in this version). [HIGH confidence — verified via PyPI and changelog] |
| requests-cache | 1.3.1 | SQLite-backed HTTP cache for nba_api calls | Drop-in `CachedSession` wraps `requests.Session`; inject into nba_api via `NBAHTTP.set_session()`. Eliminates redundant API calls during feature engineering and training. Default SQLite backend requires zero infrastructure. [HIGH confidence — verified via PyPI and official docs] |
| SQLite (stdlib) | — | Local storage for cached API responses and pre-computed feature tables | Zero-dependency (Python stdlib). requests-cache uses it by default. Also use for storing pre-computed training datasets so retraining doesn't re-fetch from NBA API. No need for PostgreSQL at this scale. [HIGH confidence] |

**Data flow:** nba_api → requests-cache (SQLite) → pandas DataFrames → feature engineering → training dataset (SQLite or parquet) → LightGBM training → model artifact (joblib).

### Feature Engineering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pandas | ≥2.2 | Rolling windows, group-by aggregations, feature matrix construction | Already in V1. V2 uses `groupby().rolling()` for player-specific windows (L5, L10, L20), `expanding()` for season-to-date, and `ewm()` for exponentially-weighted recent form. No additional feature engineering library needed — pandas handles this domain well. [HIGH confidence] |
| numpy | ≥1.26 | Numerical operations underlying pandas and LightGBM | Already in V1. Pinned as transitive dependency of scikit-learn 1.8.0 (requires ≥1.24.1). [HIGH confidence] |

**No dedicated sports feature engineering library recommended.** The NBA prop domain requires custom features (opponent defensive rating vs position, rest days, back-to-back flags, pace context, minutes stability) that don't map to any off-the-shelf library. Pandas rolling/expanding/ewm operations are the standard tool. Feature engineering is the competitive advantage — it should be bespoke, not library-delegated.

### Back-Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Custom walk-forward engine (built in-house) | — | Time-series-aware back-testing for prop predictions | **No standard sports back-testing framework exists for prop-level prediction.** The open-source options (model-backtester, nba-prop-analytics) are Jupyter-notebook experiments, not reusable libraries. Build a simple walk-forward evaluator: train on seasons 1..N, predict season N+1, slide forward. Track hit rate, Brier score, calibration curves, and ROI by confidence bucket. ~200-300 lines of Python using pandas + scikit-learn metrics. [HIGH confidence — verified by surveying available frameworks] |

**Why not an existing framework:**
- `lexcion/model-backtester` — Jupyter-only, Bet365-specific, no prop support
- `freshened/nba-prop-analytics` — Tied to The Odds API (paid), Monte Carlo focused
- `NBA-Betting/NBA_Betting` — AutoGluon-based, game outcome focus, not prop-level
- Financial back-testing libraries (backtrader, zipline) — wrong domain (sequential portfolio, not independent prop bets)

### News & Sentiment — Keyword Flagging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| gnews | 0.4.3 | Keyword search for player news (injury, trade, arrest, DNP) | Scrapes Google News RSS — no API key required for basic use. `get_news("LeBron James injury")` returns recent articles. Free, lightweight, 141+ countries. Use for binary flags ("has recent negative news?"), not full NLP. [MEDIUM confidence — verified via PyPI; depends on Google News RSS availability which can change] |

**Keyword strategy:** Search `"{player_name} {keyword}"` for keywords: `injury`, `out`, `doubtful`, `questionable`, `trade`, `arrest`, `suspension`, `DNP`, `rest`, `load management`. Return boolean flags per keyword category (injury_flag, trade_flag, disciplinary_flag). No sentiment scoring — binary presence/absence is sufficient for V2.

**Why not a paid news API:** GNews (the API service at gnews.io) offers 100 req/day free tier but requires API key. The `gnews` Python package scrapes Google News directly — no key needed for basic use. NewsAPI.org, Newscatcher, NewsDataHub all have tight free tiers (50-100 req/day) that won't scale to checking 400+ active NBA players. For V2, the gnews scraper is the right tradeoff.

### Calibration Pipeline

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| scikit-learn `CalibratedClassifierCV` | (part of 1.8.0) | Post-hoc probability calibration | LightGBM's raw `predict_proba` outputs are often poorly calibrated — they reflect tree leaf distributions, not true probabilities. Use `CalibratedClassifierCV(clf, cv='prefit', method='isotonic')` on a held-out validation set. Isotonic > Platt for this use case (non-linear calibration mapping, dataset large enough at 100K+ rows to avoid overfitting). [HIGH confidence — verified via scikit-learn docs] |

**Calibration workflow:**
1. Split data: train (70%) / calibration (15%) / test (15%) — temporal split, not random
2. Train LightGBM on train set with early stopping on calibration set
3. Fit `CalibratedClassifierCV(prefit)` on calibration set
4. Evaluate on test set with Brier score and calibration curves
5. Serialize calibrated pipeline as single joblib artifact

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Classifier | LightGBM 4.6.0 | XGBoost (already in V1) | LightGBM trains 2-5x faster on this data shape; native categorical feature support avoids one-hot encoding explosion for team/player IDs; leaf-wise growth better for deep interaction features. XGBoost is fine but LightGBM is the better fit. |
| Classifier | LightGBM 4.6.0 | CatBoost | Slower training than LightGBM; main advantage (ordered target encoding) less relevant when we're doing our own feature engineering. Community and tooling ecosystem (Optuna, SHAP) is deeper for LightGBM. |
| Hyperparameter tuning | Optuna 4.8.0 | scikit-learn GridSearchCV | Grid search is exhaustive and slow; Optuna's Bayesian optimization + LightGBM-specific stepwise tuner finds good hyperparameters in 1/10th the time. |
| Hyperparameter tuning | Optuna 4.8.0 | Ray Tune | Overkill for single-machine training. Ray Tune is for distributed hyperparameter search — not needed when training takes minutes, not hours. |
| Model serialization | joblib 1.5.3 | LightGBM native `.bst` save | joblib serializes the entire scikit-learn pipeline (scaler + LightGBM + calibrator) as one artifact. Native `.bst` only saves the booster — would need separate serialization for pre/post-processing steps. |
| Model serialization | joblib 1.5.3 | MLflow | Heavy dependency for model registry, experiment tracking, deployment. Overkill for a single-model local app. If model count grows (per-stat models, A/B testing), revisit. |
| Scheduling | APScheduler 3.11.1 | Celery + Redis | Celery requires a message broker (Redis/RabbitMQ) — unnecessary infrastructure for a single periodic training job. APScheduler runs in-process. |
| Scheduling | APScheduler 3.11.1 | OS cron | Cron works but requires system-level configuration outside the Docker container. APScheduler is Python-native and configurable in code. |
| Data cache | requests-cache + SQLite | PostgreSQL | PostgreSQL adds a third container to Docker Compose, needs migrations, schema management. SQLite is zero-config and sufficient for caching + training data storage at NBA-scale volumes (~500K rows over 5 seasons). |
| Data cache | requests-cache + SQLite | Redis | Redis is volatile by default (loses data on restart). SQLite persists to disk. Redis would require a fourth container. |
| News search | gnews 0.4.3 | NewsAPI.org | 100 req/day free tier with API key. Not enough for scanning 400+ players. gnews scrapes Google News directly. |
| News search | gnews 0.4.3 | Full NLP (Hugging Face transformers) | Massive dependency (2+ GB), slow inference, and overkill for "is this player injured?" — keyword matching catches 95% of actionable signals. PROJECT.md explicitly marks full NLP as out of scope. |
| Back-testing | Custom walk-forward | backtrader / zipline | Financial back-testing libraries model sequential portfolio P&L. Sports prop bets are independent events evaluated by hit rate and calibration — different evaluation paradigm. |
| Explainability | SHAP 0.51.0 | LightGBM built-in feature importance | Built-in importance (`split` or `gain`) is global only and doesn't explain individual predictions. SHAP provides per-prediction explanations ("opponent defense contributed +12% to over probability"). |

## Installation

```bash
# V2 new dependencies (add to server/requirements.txt)
# ML Core
lightgbm==4.6.0
optuna==4.8.0
optuna-integration==4.8.0
shap==0.51.0

# Model lifecycle
joblib==1.5.3
APScheduler==3.11.1

# Data pipeline
requests-cache==1.3.1

# News
gnews==0.4.3

# Pin existing V1 deps (currently unpinned)
scikit-learn==1.8.0
pandas>=2.2.0
numpy>=1.26.0
```

**Remove from V1:**
```bash
# Drop these from requirements.txt
google-generativeai  # Gemini summaries being removed per PROJECT.md
xgboost              # Replaced by LightGBM as primary classifier
```

**Keep from V1 (no version change needed):**
- `fastapi`, `uvicorn` — API layer unchanged
- `nba_api` — update to 1.11.4 and migrate deprecated endpoints
- `pydantic` — request/response models unchanged

## Dependency Compatibility Notes

- scikit-learn 1.8.0 requires Python ≥3.11 — V1 already uses Python 3.11, so no change needed
- LightGBM 4.6.0 requires scikit-learn ≥0.24.2 — satisfied by 1.8.0
- SHAP 0.51.0 requires Python ≥3.11 — satisfied
- nba_api 1.11.4 requires Python ≥3.10 — satisfied
- All dependencies are compatible with Python 3.11 and 3.12

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| **TensorFlow / PyTorch** | Deep learning is overkill for tabular prop prediction with ~100K rows and ~50 features. LightGBM will outperform neural nets here and train in seconds instead of minutes. |
| **MLflow / Weights & Biases** | Experiment tracking infrastructure for teams. Single-developer project with one model — joblib + a JSON metadata file is sufficient. Revisit if model count grows. |
| **Airflow / Prefect / Dagster** | Workflow orchestrators for multi-step DAGs across services. The training pipeline is a single Python script run on a schedule — APScheduler in-process is enough. |
| **PostgreSQL / MongoDB** | Additional container + schema management. SQLite handles the data volumes (500K rows) and concurrent reads from a single FastAPI process fine. |
| **Celery / Redis queue** | Message broker infrastructure for distributed task processing. One periodic training job doesn't need a task queue. |
| **dbt / Great Expectations** | Data transformation and quality tools for data warehouse pipelines. The data source is a single API (nba_api) → pandas → SQLite. No warehouse, no complex transforms. |
| **Streamlit / Dash** | Alternative frontend frameworks. V1 already has a React + MUI frontend — rebuilding in a Python dashboard framework would be a regression. |
| **The Odds API** | Paid sportsbook odds data. Explicitly deferred to future milestone per PROJECT.md. |
| **Hugging Face transformers** | 2+ GB dependency for NLP sentiment. Keyword matching on news headlines is sufficient for V2's needs. |

## Sources

- LightGBM 4.6.0: [PyPI](https://pypi.org/project/lightgbm/), [Official Docs](https://lightgbm.readthedocs.io/en/stable/)
- scikit-learn 1.8.0: [PyPI](https://pypi.org/project/scikit-learn/1.8.0/), [Calibration Docs](https://scikit-learn.org/stable/api/sklearn.calibration.html)
- Optuna 4.8.0: [PyPI](https://pypi.org/project/optuna/), [LightGBMTuner Docs](https://optuna-integration.readthedocs.io/en/stable/reference/generated/optuna_integration.lightgbm.LightGBMTuner.html)
- SHAP 0.51.0: [PyPI](https://pypi.org/project/shap/), [GitHub](https://github.com/shap/shap)
- joblib 1.5.3: [PyPI](https://pypi.org/project/joblib/)
- APScheduler 3.11.1: [PyPI](https://pypi.org/project/apscheduler/3.11.1/)
- requests-cache 1.3.1: [PyPI](https://pypi.org/project/requests-cache/), [Official Docs](https://requests-cache.readthedocs.io/en/main)
- nba_api 1.11.4: [PyPI](https://pypi.org/project/nba_api/), [GitHub](https://github.com/swar/nba_api)
- gnews 0.4.3: [PyPI](https://pypi.org/project/gnews/), [Docs](https://gnews.readthedocs.io/en/latest/)
- CalibratedClassifierCV: [scikit-learn docs](https://scikit-learn.org/stable/auto_examples/calibration/plot_calibration.html), [Stack Overflow verification](https://stackoverflow.com/questions/72163596)
- LightGBM probability calibration: [Stack Exchange discussion](https://stats.stackexchange.com/questions/372327)
- nba_api multi-season extraction: [Stack Overflow](https://stackoverflow.com/questions/74648245)
- nba_api session injection: [GitHub PR #486](https://github.com/swar/nba_api/pull/486)

---

*Stack research: 2026-03-22*
