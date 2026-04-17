# Codebase Structure

**Analysis Date:** 2026-04-17

## Directory Layout

```
HoopProphet/
├── hoopprophet/               # React frontend (CRA)
│   ├── public/                # Static assets (HTML template, favicon)
│   ├── src/
│   │   ├── App.js             # Single monolithic React component (~590 lines)
│   │   ├── index.js           # React entry point (ReactDOM.createRoot)
│   │   └── assets/
│   │       └── hoopprophet-logo.svg
│   ├── Dockerfile             # Node 20 Alpine → builds and serves static files
│   ├── package.json           # React 19, MUI 7, framer-motion, react-scripts
│   └── package-lock.json
├── server/                    # Python backend
│   ├── app.py                 # FastAPI application (all endpoints)
│   ├── __init__.py            # Empty
│   ├── Dockerfile             # Python 3.11 slim, uvicorn
│   ├── requirements.txt       # FastAPI, nba_api, sklearn, xgboost, gemini, etc.
│   ├── data/
│   │   ├── .gitkeep
│   │   ├── features.parquet   # Feature matrix output from pipeline
│   │   └── hoopprophet.db     # SQLite database (gitignored)
│   ├── ml/                    # Legacy ML modules (live per-request)
│   │   ├── dataset.py         # NBA API data collection, dataset building
│   │   ├── model_train.py     # Model training (LR/XGB), prediction, Gemini summary
│   │   └── prop_line.py       # Career average prop lines from NBA API
│   ├── pipeline/              # Batch data pipeline
│   │   ├── __init__.py        # Constants: SEASONS, paths
│   │   ├── ingest.py          # CLI orchestrator for data collection
│   │   ├── nba_client.py     # Rate-limited, cached NBA API client
│   │   ├── feature_config.py  # Configuration: stat columns, windows, thresholds
│   │   ├── features.py        # Feature pipeline orchestrator
│   │   ├── collectors/
│   │   │   ├── __init__.py
│   │   │   ├── game_logs.py   # Player game log collection
│   │   │   ├── rosters.py     # Team roster collection
│   │   │   ├── schedules.py   # Team schedule collection
│   │   │   └── team_stats.py  # Team advanced stats collection
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── contextual_features.py  # Rest days, home/away, opponent defense
│   │   │   ├── dnp_synthesis.py        # Synthesize Did Not Play rows
│   │   │   ├── matchup_features.py     # Historical vs-opponent averages
│   │   │   ├── rolling_features.py      # Rolling averages/std for stat windows
│   │   │   └── target_generator.py     # Long-format target generation (hit/miss)
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── connection.py   # SQLite connection with WAL mode
│   │       ├── queries.py     # All SQL query functions
│   │       └── schema.py      # Table DDL (players, teams, game_logs, etc.)
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py         # Pytest fixtures (tmp_db, sample_game_log_df, feature_db)
│       ├── test_contextual_features.py
│       ├── test_db.py
│       ├── test_dnp_synthesis.py
│       ├── test_feature_pipeline.py
│       ├── test_ingest.py
│       ├── test_nba_client.py
│       └── test_rolling_features.py
├── docker-compose.yml          # Backend + frontend services
├── pyproject.toml              # Pytest config (testpaths, timeout)
└── README.md
```

## Directory Purposes

**`hoopprophet/`:**
- Purpose: React single-page application frontend
- Contains: All UI code, styling (MUI theme), and static assets
- Key files: `hoopprophet/src/App.js` (entire application), `hoopprophet/package.json` (dependencies)

**`server/ml/`:**
- Purpose: Legacy per-request ML prediction modules
- Contains: Live NBA API calls, model training, and prediction logic used by `app.py`
- Key files: `server/ml/dataset.py`, `server/ml/model_train.py`, `server/ml/prop_line.py`

**`server/pipeline/`:**
- Purpose: Batch data collection and feature engineering pipeline
- Contains: Collectors (data acquisition), processors (feature computation), DB layer, and CLI orchestrator
- Key files: `server/pipeline/ingest.py`, `server/pipeline/features.py`, `server/pipeline/nba_client.py`, `server/pipeline/feature_config.py`

**`server/pipeline/collectors/`:**
- Purpose: NBA API data acquisition modules
- Contains: One module per data domain (game logs, rosters, schedules, team stats)
- Each collector function follows the signature `(client, conn, seasons) -> dict` pattern

**`server/pipeline/processors/`:**
- Purpose: Feature transformation functions
- Contains: Rolling features, contextual features, matchup features, DNP synthesis, target generation
- Key files: `server/pipeline/processors/rolling_features.py`, `server/pipeline/processors/target_generator.py`

**`server/pipeline/db/`:**
- Purpose: Database layer (SQLite)
- Contains: Schema DDL, connection factory, and query helper functions
- Key files: `server/pipeline/db/schema.py`, `server/pipeline/db/queries.py`

**`server/data/`:**
- Purpose: Runtime data storage
- Contains: SQLite database (`hoopprophet.db`), Parquet feature matrix (`features.parquet`), and NBA API HTTP cache
- Note: `.db` and `.sqlite` files are gitignored; `features.parquet` is committed

**`server/tests/`:**
- Purpose: Backend test suite (pytest)
- Contains: Unit and integration tests for pipeline components
- Key files: `server/tests/conftest.py` (shared fixtures), `server/tests/test_*.py`

## Key File Locations

**Entry Points:**
- `hoopprophet/src/index.js`: React app bootstrapper
- `server/app.py`: FastAPI server entry point with all REST endpoints
- `server/pipeline/ingest.py`: CLI pipeline runner (`python -m server.pipeline.ingest`)

**Configuration:**
- `hoopprophet/package.json`: Frontend dependencies, scripts, proxy config
- `server/requirements.txt`: Python dependencies
- `server/pipeline/__init__.py`: Pipeline constants (SEASONS, DB_PATH, CACHE_PATH, DATA_DIR)
- `server/pipeline/feature_config.py`: Feature engineering configuration (stat columns, window sizes, thresholds)
- `pyproject.toml`: Pytest configuration (testpaths, timeout)
- `docker-compose.yml`: Docker service definitions and environment variables
- `hoopprophet/package.json` → `"proxy": "http://backend:8000"`: Dev API proxy

**Core Logic:**
- `server/ml/model_train.py`: ML model training, prediction, and Gemini AI summary
- `server/ml/dataset.py`: Live dataset construction from NBA API
- `server/ml/prop_line.py`: Prop line (career average) retrieval
- `server/pipeline/features.py`: Feature pipeline orchestrator
- `server/pipeline/nba_client.py`: Cached, rate-limited NBA API client
- `hoopprophet/src/App.js`: Entire frontend application

**Database:**
- `server/pipeline/db/schema.py`: Table DDL (players, teams, player_game_logs, team_stats, team_rosters, team_schedules, collection_progress)
- `server/pipeline/db/queries.py`: Upsert, insert, and read query functions
- `server/pipeline/db/connection.py`: SQLite connection factory with WAL mode

**Testing:**
- `server/tests/conftest.py`: Shared pytest fixtures
- `server/tests/test_*.py`: Individual test modules

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `model_train.py`, `dnp_synthesis.py`)
- React: `PascalCase.js` for components (`App.js`), `camelCase.js` for entry (`index.js`)
- Test files: `test_<module_name>.py` (e.g., `test_rolling_features.py`, `test_nba_client.py`)

**Directories:**
- Python packages: `snake_case/` (e.g., `collectors/`, `processors/`, `db/`)
- Top-level: `kebab-case/` for project root dirs (`hoopprophet/`)

**Python Functions:**
- Public functions: `snake_case` (e.g., `build_dataset()`, `get_player_id()`, `compute_rolling_features()`)
- Private helpers: `_leading_underscore` (e.g., `_extract_opponent()`, `_get_player_team_tenure()`, `_parse_minutes()`, `_run_collection()`)

**Python Variables/Constants:**
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `STAT_COLS`, `PRIMARY_STATS`, `GAMELOG_COLUMN_MAP`, `MIN_DELAY`)
- Regular variables: `snake_case` (e.g., `player_id`, `opponent_team_abv`)

**React:**
- Components: `PascalCase` function components (only `App`)
- State variables: `camelCase` with `useState` pattern (e.g., `selectedPlayer`, `predicting`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE`)

## Where to Add New Code

**New REST Endpoint:**
- Add endpoint handler in `server/app.py`
- Add Pydantic model in `server/app.py` (models are defined inline alongside endpoints)
- Add corresponding `fetch()` call in `hoopprophet/src/App.js`

**New ML Model or Prediction Feature:**
- Implementation: `server/ml/dataset.py` (data features) or `server/ml/model_train.py` (model logic)
- Integrate via `server/app.py` `/predict` endpoint

**New Pipeline Collector:**
- Create `server/pipeline/collectors/<domain>.py` following the signature pattern: `(client: NBAClient, conn: sqlite3.Connection, seasons: list[str] = None) -> dict`
- Add schema table in `server/pipeline/db/schema.py`
- Add query functions in `server/pipeline/db/queries.py`
- Register in `server/pipeline/ingest.py` `_run_collection()`

**New Feature Processor:**
- Create `server/pipeline/processors/<feature_name>.py` with a function taking a DataFrame and returning enriched DataFrame
- Register in `server/pipeline/features.py` `run_feature_pipeline()`
- Add config constants to `server/pipeline/feature_config.py` if needed

**New Frontend Component:**
- Currently the entire UI is in `hoopprophet/src/App.js` — there is no component decomposition
- If breaking into components: create `hoopprophet/src/components/<ComponentName>.js`

**New Test:**
- Create `server/tests/test_<module_name>.py`
- Use fixtures from `server/tests/conftest.py` (`tmp_db`, `sample_game_log_df`, `feature_db`)
- Run: `pytest server/tests/`

## Special Directories

**`server/data/`:**
- Purpose: Runtime data storage (SQLite DB, Parquet features, HTTP cache)
- Generated: Yes (pipeline creates `hoopprophet.db` and `nba_cache.sqlite`)
- Committed: Partially (`.gitkeep` and `features.parquet` are committed; `*.db` and `*.sqlite` are gitignored)

**`server/pipeline/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (gitignored via `__pycache__/`)

**`.pytest_cache/`:**
- Purpose: Pytest cache directory
- Generated: Yes
- Committed: No (gitignored)

**`hoopprophet/build/`:**
- Purpose: React production build output (generated by `npm run build`)
- Generated: Yes (during Docker build or `npm run build`)
- Committed: No (typically gitignored by CRA defaults)

---

*Structure analysis: 2026-04-17*