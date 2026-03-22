# Architecture Research

**Domain:** NBA prop betting analytics platform (ML-powered)
**Researched:** 2026-03-22
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Dashboard    │  │  Player      │  │  Backtest    │                  │
│  │  (Best Picks) │  │  Search View │  │  Results     │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         └─────────────────┼─────────────────┘                          │
│                           ↓                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                          API LAYER (FastAPI)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  /predictions │  │  /players    │  │  /backtest   │  │  /news     │  │
│  │  /picks       │  │  /teams      │  │  /calibration│  │  /health   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │                 │                 │                 │         │
├─────────┴─────────────────┴─────────────────┴─────────────────┴─────────┤
│                       SERVICE / INFERENCE LAYER                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                     │
│  │  Model Serving       │  │  News Search          │                    │
│  │  (load artifact,     │  │  (keyword matching    │                    │
│  │   predict proba)     │  │   against RSS/API)    │                    │
│  └──────────┬───────────┘  └──────────────────────┘                     │
│             │                                                           │
├─────────────┴───────────────────────────────────────────────────────────┤
│                     OFFLINE PIPELINE LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Data Ingest  │  │  Feature     │  │  Model       │  │  Backtest  │  │
│  │  (NBA API →   │  │  Engineering │  │  Training    │  │  Engine    │  │
│  │   raw store)  │  │  (raw →      │  │  (LightGBM   │  │  (walk-    │  │
│  │              │  │   features)  │  │   → artifact) │  │   forward) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬─────┘  │
│         │                 │                 │                 │         │
├─────────┴─────────────────┴─────────────────┴─────────────────┴─────────┤
│                          DATA LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  Raw Store    │  │  Feature     │  │  Model       │                  │
│  │  (Parquet)    │  │  Store       │  │  Artifacts   │                  │
│  │              │  │  (Parquet)   │  │  (joblib)    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Data Ingest** | Pull game logs from NBA API, store as raw Parquet files partitioned by season | Python scripts using `nba_api`, write to `data/raw/` as Parquet |
| **Feature Engineering** | Transform raw game logs into ML-ready feature matrices with rolling stats, opponent context, rest days, pace | Pandas pipeline reading raw Parquet, writing to `data/features/` |
| **Model Training** | Train unified LightGBM classifier on feature store, output model artifact + metadata | LightGBM + scikit-learn, `joblib.dump()` to `models/` directory |
| **Backtest Engine** | Walk-forward validation of model against held-out historical seasons | Temporal splits on feature store, re-train per window, aggregate metrics |
| **Model Serving** | Load saved model artifact at API startup, serve predictions on request | `joblib.load()` once at startup, cached in memory |
| **API Layer** | REST endpoints for predictions, picks, players, backtest results, news | FastAPI with Pydantic schemas, structured logging |
| **News Search** | Keyword scan for injury/trade/arrest flags per player | RSS feed or web scrape, keyword matching, cache results |
| **Frontend** | Dashboard of daily best picks, player search with hit rates, backtest explorer | React with component architecture, Recharts for visualizations |

## Recommended Project Structure

```
HoopProphet/
├── docker-compose.yml              # Orchestrates all services
├── README.md
│
├── server/                          # Backend monolith
│   ├── Dockerfile
│   ├── requirements.txt             # Pinned dependencies
│   ├── app.py                       # FastAPI app, routes, startup hooks
│   │
│   ├── api/                         # Route handlers (thin)
│   │   ├── predictions.py           # /predict, /picks endpoints
│   │   ├── players.py               # /players, /player/{name}
│   │   ├── teams.py                 # /teams, /team/{name}
│   │   ├── backtest.py              # /backtest endpoints
│   │   └── news.py                  # /news/{player} endpoint
│   │
│   ├── services/                    # Business logic
│   │   ├── model_serving.py         # Load artifact, predict_proba, top picks
│   │   ├── feature_service.py       # On-demand feature computation for today's games
│   │   ├── news_service.py          # Keyword search logic
│   │   └── backtest_service.py      # Serve cached backtest results
│   │
│   ├── pipeline/                    # Offline training pipeline
│   │   ├── ingest.py                # NBA API → raw Parquet
│   │   ├── features.py              # Raw → feature engineering
│   │   ├── train.py                 # Feature store → LightGBM → artifact
│   │   ├── calibrate.py             # Platt scaling / isotonic regression
│   │   ├── backtest.py              # Walk-forward validation engine
│   │   └── run_pipeline.py          # Orchestrator: ingest → features → train → calibrate
│   │
│   ├── core/                        # Shared utilities
│   │   ├── config.py                # Pydantic Settings, env vars
│   │   ├── nba_client.py            # Centralized NBA API wrapper with rate limiting
│   │   └── logging.py               # Structured logging setup
│   │
│   ├── models/                      # Model artifacts (gitignored, Docker-volume-mounted)
│   │   ├── current/                 # Currently serving model
│   │   │   ├── model.joblib         # LightGBM binary
│   │   │   ├── calibrator.joblib    # Probability calibrator
│   │   │   ├── feature_columns.json # Feature schema for validation
│   │   │   └── metadata.json        # Training date, metrics, version
│   │   └── archive/                 # Previous model versions
│   │
│   ├── data/                        # Data store (gitignored, Docker-volume-mounted)
│   │   ├── raw/                     # Raw NBA API responses as Parquet
│   │   │   ├── gamelogs/            # Player game logs by season
│   │   │   ├── team_stats/          # Team defensive ratings by season
│   │   │   └── schedules/           # Game schedules
│   │   ├── features/                # Engineered feature matrices
│   │   │   └── training_set.parquet # Full training dataset
│   │   └── backtest/                # Backtest result caches
│   │       └── results.json         # Latest backtest metrics
│   │
│   └── tests/                       # pytest tests
│       ├── test_features.py
│       ├── test_model.py
│       └── test_api.py
│
└── hoopprophet/                     # React frontend
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── index.js
        ├── App.js                   # Layout shell, routing
        ├── components/
        │   ├── layout/              # Header, Sidebar, Footer
        │   ├── dashboard/           # DailyPicks, PickCard, FilterBar
        │   ├── player/              # PlayerSearch, PlayerProfile, PropTable, HitRateChart
        │   ├── backtest/            # BacktestSummary, CalibrationPlot
        │   └── common/              # LoadingSpinner, ErrorBoundary, StatBadge
        ├── hooks/                   # usePlayerSearch, usePredictions, useBacktest
        ├── services/                # API client functions
        │   └── api.js               # Centralized fetch wrapper
        ├── utils/                   # Formatters, constants
        └── assets/
```

### Structure Rationale

- **`server/pipeline/`:** Offline training code lives alongside the API but runs independently (CLI or cron). Shares `core/` utilities like `nba_client.py` and `config.py` without duplication.
- **`server/api/` + `server/services/`:** Thin routers delegate to service modules. This separates HTTP concerns from business logic, making both testable. The serving path never imports pipeline code.
- **`server/data/` + `server/models/`:** Local file-based stores, Docker-volume-mounted. Parquet for tabular data (fast reads, columnar, good pandas integration). Joblib for model artifacts. No database needed at this scale.
- **`hoopprophet/src/components/`:** Feature-grouped component folders replace the monolithic `App.js`. Each domain (dashboard, player, backtest) owns its components.

## Architectural Patterns

### Pattern 1: Offline Train / Online Serve Split

**What:** The training pipeline and the serving API are separate execution paths that share only the model artifact directory. Training writes artifacts; serving reads them.

**When to use:** Whenever model training is too slow to run per-request (LightGBM on 100K+ rows takes seconds to minutes, not milliseconds).

**Trade-offs:**
- Pro: API response time is pure inference (~5-20ms), not training (~30-120s)
- Pro: Model can be validated before serving (backtest, calibration check)
- Con: Predictions use a model that may be hours/days stale
- Con: Need a mechanism to retrain and swap the model

**Example:**

```python
# pipeline/train.py — runs offline
import joblib
from lightgbm import LGBMClassifier

def train_and_save(features_path: str, output_dir: str):
    df = pd.read_parquet(features_path)
    X, y = df.drop(columns=["hit"]), df["hit"]
    
    model = LGBMClassifier(n_estimators=500, learning_rate=0.05, max_depth=6)
    model.fit(X, y)
    
    joblib.dump(model, f"{output_dir}/model.joblib", compress=3)
    # Also save feature column order for validation
    json.dump(list(X.columns), open(f"{output_dir}/feature_columns.json", "w"))


# services/model_serving.py — runs at API startup
class ModelServer:
    def __init__(self, model_dir: str):
        self.model = joblib.load(f"{model_dir}/model.joblib")
        self.feature_cols = json.load(open(f"{model_dir}/feature_columns.json"))
    
    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(features[self.feature_cols])[:, 1]
```

### Pattern 2: Binary Classification Framing for Props

**What:** Frame every prop as a binary classification — "did this player go OVER the line?" — rather than predicting the raw stat value and comparing.

**When to use:** When users care about probability of hitting a threshold, not the point estimate.

**Trade-offs:**
- Pro: Directly outputs the quantity users need (probability)
- Pro: One unified model handles all stat types via row-level features
- Pro: LightGBM `predict_proba` outputs are well-suited for calibration
- Con: Requires a "line" value at training time — use historical median or sportsbook-derived lines
- Con: Loses the raw stat prediction (can be added as a secondary model later)

**Example:**

```python
# Feature row: one row per (player, game, stat_type, line_value)
# Target: 1 if actual_stat > line_value, else 0
{
    "player_id": 203999,
    "stat_type": "PTS",         # encoded as integer
    "line_value": 24.5,
    "rolling_5_avg": 26.2,
    "rolling_10_avg": 25.1,
    "opp_def_rating": 112.3,
    "rest_days": 2,
    "home_away": 1,
    "minutes_rolling_5": 34.8,
    "hit": 1                    # target: actual PTS was 28 > 24.5
}
```

### Pattern 3: Feature Store as Parquet Files

**What:** Store pre-computed feature matrices as Parquet files on disk rather than computing features on every request or using a database.

**When to use:** When the dataset fits in memory (100K-1M rows), there's no real-time feature requirement, and the team is small.

**Trade-offs:**
- Pro: Zero infrastructure — no database to manage, Parquet reads are fast (~100ms for 500K rows)
- Pro: Parquet preserves dtypes, supports column pruning, compresses well
- Pro: Pandas reads Parquet natively, no ORM or query language needed
- Con: No concurrent write safety (fine for single-writer pipeline)
- Con: No query engine for ad-hoc analysis (use DuckDB if needed later)

### Pattern 4: Walk-Forward Backtesting

**What:** Validate model accuracy by simulating what would have happened if the model had been deployed historically. Train on data before date T, predict on date T, slide forward.

**When to use:** Always, for any time-series prediction system. Standard k-fold cross-validation leaks future data.

**Trade-offs:**
- Pro: Most realistic estimate of live model performance
- Pro: Catches temporal drift (model accuracy decay over a season)
- Con: Computationally expensive — retrains model for each time window
- Con: Requires multi-season historical data to have enough windows

**Example:**

```python
# Walk-forward: train on seasons before test_season, predict test_season
def walk_forward_backtest(features: pd.DataFrame, seasons: list[str]):
    results = []
    for i, test_season in enumerate(seasons[2:], start=2):
        train = features[features["season"].isin(seasons[:i])]
        test = features[features["season"] == test_season]
        
        model = LGBMClassifier(...)
        model.fit(train.drop(columns=["hit"]), train["hit"])
        
        probs = model.predict_proba(test.drop(columns=["hit"]))[:, 1]
        results.append(evaluate(test["hit"], probs, test_season))
    
    return pd.DataFrame(results)
```

## Data Flow

### Core Data Pipeline (Offline)

```
NBA API (nba_api)
    │
    ↓ ingest.py (rate-limited, cached)
    │
Raw Parquet Store (data/raw/)
    │  gamelogs/     → player game logs by season
    │  team_stats/   → team defensive ratings, pace
    │  schedules/    → game dates, opponents, home/away
    │
    ↓ features.py
    │
Feature Store (data/features/training_set.parquet)
    │  Per row: (player_id, game_date, stat_type, line_value,
    │            rolling_5_avg, rolling_10_avg, rolling_20_avg,
    │            opp_def_rank, rest_days, home_away, minutes_ctx,
    │            consistency_std, matchup_history, pace_factor,
    │            season, hit)
    │
    ├──→ train.py → model.joblib + metadata.json (models/current/)
    │         │
    │         ↓ calibrate.py
    │         calibrator.joblib (models/current/)
    │
    └──→ backtest.py → results.json (data/backtest/)
```

### Prediction Request Flow (Online)

```
[User opens dashboard or searches player]
    │
    ↓ React frontend
    │  GET /predictions/daily-picks   OR
    │  GET /predictions/player/{id}?stat_types=PTS,AST&line=24.5
    │
    ↓ FastAPI router (api/predictions.py)
    │
    ↓ model_serving.py
    │  1. Compute live features for today's game
    │     (feature_service.py → rolling stats from cached raw data + today's context)
    │  2. model.predict_proba(features) → raw probability
    │  3. calibrator.predict(raw_prob) → calibrated probability
    │  4. Rank by probability, return top picks
    │
    ↓ JSON response
    │  { player, stat_type, line, probability, hit_rates: {L5, L10, L20, season} }
    │
    ↓ React renders PickCard / PropTable
```

### Key Data Flows

1. **Daily picks generation:** Pipeline runs overnight → fresh features → model predicts all active players × their top stat types → API caches ranked results → dashboard serves them instantly.

2. **Player search prediction:** User picks a player → API computes live features for that player's next game → model predicts across stat types → returns probabilities + hit rates.

3. **Backtest results:** Pipeline runs walk-forward validation after each retrain → stores aggregate metrics (accuracy, calibration, ROI by stat type) as JSON → frontend reads via `/backtest` endpoint.

4. **News flags:** Separate lightweight service polls RSS/news feeds → matches player names + keywords (injury, trade, DNP, arrest) → flags surface as warnings alongside predictions.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-100 users (current target) | Monolith is correct. Single Docker Compose, Parquet files, in-memory model. No database needed. |
| 100-1K users | Add Redis for caching daily picks and feature computations. Pin Uvicorn workers to 2-4. Parquet store still fine. |
| 1K+ users | Move Parquet store to PostgreSQL or DuckDB for concurrent reads. Consider pre-computing all predictions daily rather than on-demand. |

### Scaling Priorities

1. **First bottleneck: NBA API rate limits.** The `nba_api` package hits NBA.com endpoints that throttle aggressively. Mitigation: aggressive caching of raw data in Parquet, only fetch deltas (new games since last ingest). The offline pipeline handles this; the API should never call NBA API directly for predictions.

2. **Second bottleneck: Feature computation latency.** Computing rolling stats for a single player takes ~50-200ms with Pandas. For the daily picks dashboard (generating predictions for 400+ active players), this becomes 20-80 seconds. Mitigation: pre-compute all features during the pipeline run, cache in Parquet, serve from cache.

## Anti-Patterns

### Anti-Pattern 1: Training in the Request Path

**What people do:** V1 does this — every `/predict` call runs `train_models()` which fits Linear Regression and XGBoost with 10×10 repeated k-fold CV.

**Why it's wrong:** Each prediction takes 10-30 seconds. Users wait. NBA API gets hammered. Models trained on ~60 rows per player are statistically unreliable.

**Do this instead:** Train offline on the full multi-season dataset, save the artifact, load once at API startup. Prediction becomes a ~5ms `predict_proba` call.

### Anti-Pattern 2: Per-Player Model Training

**What people do:** Train a separate model for each player (V1's approach).

**Why it's wrong:** Most players have 60-80 games of data — far too few for a reliable model. The model can't generalize across players or learn from league-wide patterns.

**Do this instead:** Train one unified model across all players. Encode `player_id` or player archetype as a feature. 100K+ training rows enable the model to learn general patterns (e.g., "players facing bottom-5 defenses score more") while player-specific features (rolling averages, usage rate) capture individual tendencies.

### Anti-Pattern 3: Random K-Fold CV for Time-Series Data

**What people do:** Use `RepeatedKFold` for cross-validation on game log data.

**Why it's wrong:** Random splits let the model train on February games to predict January games — temporal data leakage. Model appears accurate during validation but fails in production.

**Do this instead:** Use `TimeSeriesSplit` or walk-forward validation. Only train on data chronologically before the test set.

### Anti-Pattern 4: Predicting Raw Stats Instead of Probabilities

**What people do:** Predict "Player X will score 24.7 points" and compare to a line.

**Why it's wrong:** A point estimate of 24.7 vs a line of 24.5 provides no confidence information. Is it 51% likely or 90% likely? Bettors need the probability, not the point estimate.

**Do this instead:** Frame as binary classification: P(PTS > 24.5). LightGBM's `predict_proba` directly outputs what bettors need. Calibrate the probabilities so "70% confident" actually hits ~70% of the time.

### Anti-Pattern 5: Monolithic Frontend Component

**What people do:** Put all UI logic in one 600-line component (V1's `App.js`).

**Why it's wrong:** Impossible to maintain, test, or iterate on individual features. State management becomes tangled.

**Do this instead:** Feature-based component folders. Each domain (dashboard, player, backtest) owns its components, hooks, and local state. Shared layout components handle structure.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| NBA API (`nba_api`) | Python package, REST under the hood | Rate limited — add 0.5-1s delays between calls. Cache everything. Only call during pipeline runs, never in the request path. |
| NBA CDN (`cdn.nba.com`) | Direct URL construction for headshots/logos | No auth needed. URLs follow pattern: `cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png`. Stable and fast. |
| News sources (RSS/web) | RSS feed parsing or simple HTTP scrapes | Keep lightweight. Keyword matching, not NLP. Cache for 15-30 minutes. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Pipeline → Model Store | File system (write joblib + metadata) | Pipeline writes to `models/current/`. API reads at startup. Atomic swap: write to temp dir, then rename. |
| Pipeline → Feature Store | File system (write Parquet) | Pipeline writes `data/features/training_set.parquet`. Backtest engine also reads this. |
| API → Model Server | In-process Python call | `ModelServer` class loaded at FastAPI startup via `@app.on_event("startup")`. No network hop. |
| API → Feature Service | In-process Python call | Computes live features from cached raw data. Shares `nba_client.py` with pipeline but should read from cached Parquet, not call NBA API. |
| Frontend → API | HTTP REST (JSON) | Standard fetch/axios calls. All prediction data comes through the API — frontend never computes ML features. |

## Build Order Implications

Components have strict dependencies that determine phase ordering:

```
1. Data Ingest          (no dependencies — can start immediately)
   ↓
2. Feature Engineering  (requires: raw data store from #1)
   ↓
3. Model Training       (requires: feature store from #2)
   ↓
4. Model Serving API    (requires: model artifact from #3)
   ↓
5. Predictions API      (requires: serving layer from #4 + feature service)
   ↓
6. Frontend Dashboard   (requires: API endpoints from #5)

   Parallel tracks (can start after #2):
   ├── Backtest Engine   (requires: feature store from #2, reuses training code from #3)
   ├── News Search       (independent — no ML dependency)
   └── Calibration       (requires: trained model from #3, backtest data)
```

**Critical path:** Ingest → Features → Training → Serving → API → Frontend. The back-testing engine and news search can be built in parallel once the feature store exists.

**Recommended phase structure based on dependencies:**

1. **Data layer + ingestion** — Raw Parquet store, NBA API client with caching, multi-season historical data pull. Foundation for everything.
2. **Feature engineering pipeline** — Transform raw data into training features. This defines the model's input contract.
3. **Model training + calibration** — LightGBM training, Platt scaling, artifact storage. Produces the model the API will serve.
4. **API refactor + model serving** — Restructure FastAPI into routers/services, load model at startup, prediction endpoints.
5. **Back-testing engine** — Walk-forward validation, accuracy metrics, calibration plots. Can partially overlap with #4.
6. **Frontend rebuild** — Component architecture, dashboard, player search, hit rate visualizations.
7. **News search + polish** — Keyword flagging, integration with predictions, final UX tuning.

## Sources

- Production NBA prop system architecture (6-phase pipeline with 7 ML systems): najicham/nba-stats-scraper (GitHub, 2025)
- End-to-end NBA player performance prediction with cloud deployment: Felixokoth (Medium, 2025)
- FastAPI production patterns for ML serving: dev.to/apaksh (2026)
- LightGBM model persistence with joblib: mljar.com/docs, joblib docs
- Walk-forward backtesting for sports betting: wagerproof.bet, predscanner.com
- Temporal cross-validation for NBA predictions: Arvind Rangarajan (Medium, AI Builder)
- React dashboard architecture patterns: dev.to (2026), TeachMeIDEA (Recharts + TanStack Table guide)

---
*Architecture research for: NBA prop betting analytics platform*
*Researched: 2026-03-22*
