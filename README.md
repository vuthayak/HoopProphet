# HoopProphet

NBA player prop prediction platform powered by LightGBM, calibrated probability modeling, and walk-forward backtesting. HoopProphet ingests 5 seasons of NBA game data, engineers contextual and rolling features, trains a binary classifier, and serves calibrated over/under probabilities for player stat props — all with a React frontend for exploration.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Layer](#data-layer)
- [Feature Engineering Pipeline](#feature-engineering-pipeline)
- [Machine Learning Model](#machine-learning-model)
- [Prediction Serving](#prediction-serving)
- [News & Injury Alerts](#news--injury-alerts)
- [Backtesting Engine](#backtesting-engine)
- [Frontend](#frontend)
- [API Reference](#api-reference)
- [CLI Commands](#cli-commands)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Testing](#testing)

---

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────────────────────────────┐
│                 │      │              Backend (FastAPI)             │
│   React + Vite  │─────►│                                           │
│   Frontend      │◄─────│  Players ─ Teams ─ News ─ Backtest API    │
│   (port 3000)   │ REST │                                           │
└─────────────────┘      │  ┌─────────────────────────────────────┐ │
                         │  │        Service Layer                  │ │
                         │  │  player_service  prediction_service  │ │
                         │  │  hitrate_service news_service        │ │
                         │  └─────────────────────────────────────┘ │
                         │                                           │
                         │  ┌─────────────────────────────────────┐ │
                         │  │     Pipeline Layer                    │ │
                         │  │  ingest → features → train → calibrate│ │
                         │  │  artifact → backtest → metrics        │ │
                         │  └─────────────────────────────────────┘ │
                         │                                           │
                         │  ┌─────────────────────────────────────┐ │
                         │  │  SQLite DB (hoopprophet.db)          │ │
                         │  │  players, teams, game_logs, alerts   │ │
                         │  └─────────────────────────────────────┘ │
                         └──────────────────────────────────────────┘
```

**Data flow**: NBA API data is collected and cached into SQLite. The feature pipeline reads raw data, computes rolling/contextual/matchup features, generates binary targets, and writes a `features.parquet`. The training CLI runs walk-forward cross-validation, calibrates the model, and saves a `.joblib` artifact. At API startup, the artifact is loaded once into memory. Prediction requests read from the parquet, run `predict_proba` through the calibrated model, and return top props with hit rates and alert context.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, Tailwind CSS 4, React Router 7, visx charts |
| Backend | FastAPI, Uvicorn |
| Database | SQLite (WAL mode) |
| ML | LightGBM, scikit-learn (CalibratedClassifierCV), pandas, numpy |
| Data Ingestion | nba_api, requests-cache, tenacity (retry), feedparser |
| Build/Deploy | Docker, Docker Compose |
| Testing | Vitest (frontend), pytest (backend) |

---

## Project Structure

```
HoopProphet/
├── hoopprophet/              # React frontend (Vite)
│   ├── src/
│   │   ├── api/client.js     # API client with all endpoints
│   │   ├── components/       # UI components (PropCard, HitRateChart, etc.)
│   │   ├── hooks/            # Custom React hooks (usePlayerData, useBacktest, etc.)
│   │   ├── pages/            # Route pages (Home, Player, Backtest)
│   │   ├── utils/            # Constants & formatters
│   │   └── App.jsx           # Router setup
│   ├── Dockerfile
│   ├── vite.config.js
│   └── package.json
│
├── server/                   # FastAPI backend
│   ├── api/                  # Route handlers (players, teams, news, backtest)
│   ├── core/config.py        # Centralized configuration
│   ├── services/             # Business logic layer
│   │   ├── player_service.py
│   │   ├── prediction_service.py
│   │   ├── hitrate_service.py
│   │   ├── team_service.py
│   │   └── news_service.py
│   ├── pipeline/             # Data & ML pipeline
│   │   ├── collectors/       # NBA API data collectors
│   │   ├── processors/      # Feature processors
│   │   │   ├── rolling_features.py
│   │   │   ├── contextual_features.py
│   │   │   ├── matchup_features.py
│   │   │   ├── target_generator.py
│   │   │   └── dnp_synthesis.py
│   │   ├── db/               # Database schema, queries, connection
│   │   ├── artifact.py       # Model load/save/predict
│   │   ├── train.py          # LightGBM training
│   │   ├── train_config.py   # Hyperparameters & paths
│   │   ├── calibrate.py      # Isotonic/sigmoid calibration
│   │   ├── backtest.py       # Walk-forward back-testing engine
│   │   ├── backtest_metrics.py
│   │   ├── dataset.py        # Feature column selection
│   │   ├── features.py      # Full feature pipeline orchestrator
│   │   ├── feature_config.py # Stat definitions & feature config
│   │   ├── splits.py         # Walk-forward season splits
│   │   ├── metrics.py        # Log loss, Brier, calibration curves
│   │   ├── nba_client.py     # Rate-limited NBA API client
│   │   └── ingest.py         # CLI data collection orchestrator
│   ├── data/                 # Runtime data (SQLite DB, parquet, artifacts)
│   ├── tests/                # 30+ test files
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Data Layer

### SQLite Schema (hoopprophet.db)

The database stores all cached NBA data. Key tables:

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `players` | NBA player registry | `player_id`, `full_name`, `is_active`, `position`, `team_id` |
| `teams` | NBA team registry | `team_id`, `abbreviation`, `full_name` |
| `player_game_logs` | Per-game box scores | `player_id`, `game_id`, `season`, `game_date`, `matchup`, `wl`, `min`, `pts`, `reb`, `ast`, `stl`, `blk`, `fg3m`, `fgm`, `fga`, `ftm`, `fta`, `oreb`, `dreb`, `tov`, `pf`, `plus_minus`, `is_dnp` |
| `team_stats` | Advanced team metrics per season | `team_id`, `season`, `def_rating`, `off_rating`, `net_rating`, `pace` |
| `team_rosters` | Player-team-season mappings | `team_id`, `player_id`, `season` |
| `team_schedules` | Team game schedules | `team_id`, `game_id`, `season`, `game_date`, `matchup`, `wl` |
| `collection_progress` | Ingestion tracking | `entity_type`, `entity_id`, `season`, `status`, `error_message` |
| `news_items` | NBA news & RSS items | `source`, `headline`, `raw_content`, `player_id`, `published_at` |
| `player_alerts` | Deduplicated alerts per player | `player_id`, `alert_type`, `subcategory`, `severity`, `source` |

### Data Collection

The `NBAClient` class provides rate-limited, cached, retry-enabled access to the NBA API:

- **Teams & Players**: Seeded from `nba_api` static endpoints
- **Game Logs**: Per-player, per-season box scores (5 seasons: 2020-21 through 2024-25)
- **Team Rosters & Schedules**: Per-team, per-season
- **Team Advanced Stats**: Defensive/offensive rating, pace per season
- **DNP Synthesis**: Games where a player was on the roster but didn't play are synthesized as DNP rows

All API calls use `requests-cache` for HTTP caching and `tenacity` for exponential-backoff retries.

---

## Feature Engineering Pipeline

The feature pipeline (`server/pipeline/features.py`) transforms raw game logs into a long-format parquet file ready for training.

### Processing Stages

1. **Rolling Features** (`rolling_features.py`):
   - L5, L10, L20 rolling mean & standard deviation for all stat columns
   - L5, L10 rolling mean & std for secondary stats
   - Season-to-date expanding averages for primary stats
   - Combo stat rolling averages (PRA, PA, PR)
   - All rolling features are **shifted by 1** to prevent target leakage

2. **Contextual Features** (`contextual_features.py`):
   - `rest_days` — days between games (capped at 14)
   - `is_b2b` — back-to-back flag
   - `is_home` — home/away
   - `opp_def_rating`, `opp_pace` — opponent defensive rating & pace
   - `team_pace` — player's team pace
   - `position` — player position from roster data

3. **Matchup Features** (`matchup_features.py`):
   - `matchup_avg_{stat}` — player's historical average vs. specific opponent within a 2-season window

4. **Target Generation** (`target_generator.py`):
   - Converts wide-format data to long-format with one row per (player, game, stat_type, line_value)
   - For each stat, generates 7 line values centered on a rolling 20-game median (offsets: -1, -0.5, 0, +0.5, +1 in 0.5 increments)
   - Binary target: `hit = 1` if actual stat > line_value
   - Stats covered: `pts`, `reb`, `ast`, `stl`, `blk`, `fg3m`, `pra`, `pa`, `pr`, `min`

5. **DNP Synthesis** (`dnp_synthesis.py`):
   - Identifies games where a player was on the roster but recorded no stats
   - Synthesizes DNP rows with `is_dnp=1` so the model can learn rest/injury patterns

### Quality Filters

- Minimum 10 games per player-season (`MIN_GAMES_PER_SEASON`)
- DNP rows excluded from feature computation
- Stats averaging <1.0 per game excluded from line generation
- Minimum 5 non-DNP games required for default line computation

---

## Machine Learning Model

### Model Architecture

- **Algorithm**: LightGBM binary classifier (`LGBMClassifier`)
- **Objective**: `binary` (predicting over/under hit probability)
- **Unified model**: Single model across all players and stat types, with `stat_type` as a categorical feature

### Hyperparameters

| Parameter | Value |
|-----------|-------|
| n_estimators | 500 |
| learning_rate | 0.05 |
| max_depth | 6 |
| num_leaves | 31 |
| min_child_samples | 50 |
| feature_fraction | 0.8 |
| bagging_fraction | 0.8 |
| bagging_freq | 5 |
| reg_alpha | 0.1 |
| reg_lambda | 0.1 |

### Walk-Forward Training

- Expanding window temporal split across 5 seasons (2020-21 through 2024-25)
- Minimum 2 training seasons per fold
- Fold 1: train on 2020-21 + 2021-22, validate on 2022-23
- Fold 2: train on 2020-21 through 2022-23, validate on 2023-24
- Fold 3: train on 2020-21 through 2023-24, validate on 2024-25

### Probability Calibration

After training, model probabilities are calibrated using `CalibratedClassifierCV` with `cv='prefit'`:

- **Preferred**: Isotonic regression (requires ≥1,000 calibration samples and sufficient class balance)
- **Fallback**: Platt scaling (sigmoid) when isotonic is unreliable

### Model Artifact

The saved `.joblib` artifact contains:
- `model` — Raw LGBMClassifier (for feature importances)
- `calibrator` — CalibratedClassifierCV (for `predict_proba`)
- `feature_columns` — Ordered list of feature names for input validation
- `categorical_features` — `["stat_type"]` for LightGBM
- `metrics` — Per-fold training metrics
- `metadata` — Version, timestamp, calibration method

---

## Prediction Serving

At API startup, the model artifact is loaded into `app.state.model_artifact`. The prediction flow:

1. `GET /api/players/{id}/props` receives a request
2. `prediction_service.get_player_props()` computes default lines (median of last 20 non-DNP games, rounded to 0.5)
3. For each stat, reads the most recent feature row from `features.parquet` for that player/stat_type
4. Runs `artifact.predict_proba()` through the calibrated model
5. Returns top 5 props sorted by probability, each enriched with:
   - `stat`, `line`, `probability` (rounded to 1%), `direction`
   - Hit rates across L5/L10/L20/Season windows

### Default Line Computation

- Median of last 20 non-DNP games, rounded to nearest 0.5
- Combo stats (PRA, PA, PR) computed from component stat sums
- Stats excluded if average < 1.0 per game or < 5 games played
- Probability rounded to nearest 1% (prevents model reconstruction attacks)

### Graceful Degradation

If no model artifact is available at startup:
- `/api/health` reports `model_loaded: false`
- Prop endpoints return empty `top_props` but still provide `default_lines`
- All other endpoints function normally

---

## News & Injury Alerts

The `NewsService` fetches and processes NBA news from multiple sources:

### Sources

| Source | Type | URL |
|--------|------|-----|
| NBA Official Injury Report | HTML parsing | `official.nba.com/nba-injury-report/` |
| ESPN NBA RSS | Feedparser | `espn.com/espn/rss/nba/news` |
| NBA.com RSS | Feedparser | `nba.com/rss/nba_rss.xml` |

### Alert Categories

| Alert Type | Keywords | Severity |
|-----------|----------|----------|
| **OUT** | out, ruled out, sidelined, DNP | Critical |
| **INJURY** | injury, hurt, sprain, strain, knee, ankle | Warning |
| **QUESTIONABLE** | questionable, GTC, game-time decision | Warning |
| **TRADE** | traded, acquired, waived | Warning |
| **SUSPENSION** | suspended, banned | Critical |
| **G_LEAGUE** | G League, assigned to, recalled | Info |
| **REST** | rest, load management | Info |

Injury report statuses are mapped to subcategories: `PROBABLE`, `QUESTIONABLE`, `DOUBTFUL`.

### Player Matching

Fuzzy name matching handles accented characters, nicknames, and partial-name references with 80% token overlap threshold.

### Caching & Freshness

- HTTP responses cached via `requests-cache` (SQLite backend)
- TTL: 6 hours for news fetches
- Stale warning: 24 hours
- Auto-cleanup: news items older than 30 days

---

## Backtesting Engine

The walk-forward backtest evaluates model performance across historical folds:

### How It Works

1. Load `features.parquet`
2. Generate expanding-window folds (same as training)
3. For each fold: train on prior seasons → calibrate on validation data → predict on validation season
4. Collect per-prediction results: `player_id`, `game_id`, `stat_type`, `line_value`, `hit`, `predicted_proba`

### Metrics Computed

| Metric | Description |
|--------|-------------|
| **Log Loss** | Cross-entropy loss per fold |
| **Brier Score** | Mean squared error of probabilities |
| **Accuracy** | Binary classification accuracy (threshold 0.5) |
| **Calibration Curve** | Predicted vs. observed hit rates in 10 bins |
| **ECE** | Expected Calibration Error |
| **ROI** | `(accuracy - breakeven) / breakeven * 100` at -110 vig |

### API Endpoints

- `GET /api/backtest/summary` — Overall accuracy, Brier score, ROI
- `GET /api/backtest/seasons` — Per-season breakdown
- `GET /api/backtest/calibration` — 10-bin calibration curve

---

## Frontend

Built with **React 19 + Vite 8 + Tailwind CSS 4**.

### Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | HomePage | Search bar with player autocomplete |
| `/player/:playerId` | PlayerPage | Player detail with 3 tabs: Overview, Game Logs, News |
| `/backtest` | BacktestPage | Model accuracy dashboard with summary cards, season table, calibration chart |

### Key Components

- **PlayerSearch** — Debounced player search with min 2 characters
- **PlayerHeader** — Player name, position, team, alert badges
- **PropCard** — Prop prediction card with probability badge, hit rate bars, line display
- **HitRateChart** — Visual hit rate bars across L5/L10/L20/Season windows
- **GameLogTable** — Recent game log table with all box score stats
- **NewsList** — News items and alerts with freshness indicators
- **AlertBadge** — Color-coded injury/status badges (OUT=red, INJURY=orange, etc.)
- **BacktestSummary** — Summary cards (accuracy, Brier, ROI)
- **SeasonBreakdown** — Season-by-season accuracy table
- **CalibrationChart** — visx bar chart of predicted vs. observed probabilities
- **ToastProvider** — Global toast notification system

### Custom Hooks

| Hook | Purpose |
|------|---------|
| `usePlayerData` | Fetches player info, props, and alerts |
| `useGameLogs` | Fetches recent game logs |
| `useNews` | Fetches player news with refresh support |
| `useBacktest` | Fetches backtest summary, seasons, calibration |
| `useSearch` | Debounced player search |

---

## API Reference

### Players

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/players` | List all active players; `?search=name` for search |
| `GET` | `/api/players/{id}` | Player detail with default lines & alert summary |
| `GET` | `/api/players/{id}/props` | Top 5 props with ML probability & hit rates |
| `GET` | `/api/players/{id}/gamelogs` | Recent game logs; `?limit=50&seasons=2024-25` |
| `GET` | `/api/players/{id}/hitrates?stat=pts&line=20.5` | Hit rates across windows |
| `GET` | `/api/players/{id}/lines` | Default stat lines |
| `GET` | `/api/players/{id}/news` | News items & injury alerts |

### Teams

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/teams` | List all teams |
| `GET` | `/api/teams/{id}` | Team detail |

### Backtest

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/backtest/summary` | Overall accuracy, Brier score, ROI |
| `GET` | `/api/backtest/seasons` | Per-season metrics breakdown |
| `GET` | `/api/backtest/calibration` | Calibration curve bins |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check with model load status |

---

## CLI Commands

### Data Collection

```bash
# Full 5-season collection
python -m server.pipeline.ingest --full

# Refresh current season only
python -m server.pipeline.ingest --refresh

# Validate data completeness
python -m server.pipeline.ingest --validate

# Run feature engineering only
python -m server.pipeline.ingest --features-only

# Full collection + feature engineering
python -m server.pipeline.ingest --full --features

# Verbose logging
python -m server.pipeline.ingest --full -v
```

### Model Training

```bash
# Train with walk-forward validation
python -m server.pipeline.train_cli

# Custom training run
python -m server.pipeline.train_cli --help
```

### Backtesting

```bash
# Run walk-forward backtest
python -m server.pipeline.backtest_cli

# Custom backtest run
python -m server.pipeline.backtest_cli --help
```

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) and [Docker Compose](https://docs.docker.com/compose/)

### Development Quick Start

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/HoopProphet.git
   cd HoopProphet
   ```

2. **Build and run:**
   ```sh
   docker-compose up --build
   ```

3. **Access the app:**
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Only

```sh
cd hoopprophet
npm install
npm run dev
```

Set `VITE_API_BASE=http://localhost:8000` if running the backend locally.

### Backend Only

```sh
cd server
pip install -r requirements.txt
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key (optional, for AI summaries) | — |
| `VITE_API_BASE` | Backend API base URL for frontend | `""` (relative) |

The backend reads database paths and news URLs from `server/core/config.py`:

| Config | Value |
|--------|-------|
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8000` |
| `CORS_ORIGINS` | `localhost:3000`, `frontend:3000` |
| `DB_PATH` | `server/data/hoopprophet.db` |
| `PARQUET_PATH` | `server/data/features.parquet` |
| `MODEL_ARTIFACT_PATH` | `server/data/models/model.joblib` |
| `ESPN_RSS_URL` | `https://www.espn.com/espn/rss/nba/news` |
| `NBA_RSS_URL` | `https://www.nba.com/rss/nba_rss.xml` |
| `NBA_INJURY_REPORT_URL` | `https://official.nba.com/nba-injury-report/` |
| `NEWS_TTL_HOURS` | `6` |
| `NEWS_STALE_WARNING_HOURS` | `24` |
| `NEWS_CLEANUP_DAYS` | `30` |

---

## Testing

### Backend (pytest)

```sh
cd server
pytest -v
```

30+ test files covering:
- API endpoints (players, teams, news, backtest)
- Services (player, prediction, hit rate, news)
- Pipeline (ingest, features, train, calibrate, backtest, metrics, splits)
- Database (schema, queries, connection)
- Processors (rolling features, contextual features, DNP synthesis)

### Frontend (Vitest)

```sh
cd hoopprophet
npm run test
```

---

*HoopProphet — NBA prop predictions backed by walk-forward validated, probability-calibrated machine learning.*