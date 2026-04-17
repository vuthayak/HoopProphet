# Architecture

**Analysis Date:** 2026-04-17

## Pattern Overview

**Overall:** Two-service monorepo with separate frontend (React SPA) and backend (FastAPI) communicating via REST API. The backend has a dual architecture: a real-time prediction API (`server/ml/`) and a batch data pipeline (`server/pipeline/`).

**Key Characteristics:**
- Frontend is a single-page React app (CRA) with no routing — single `App.js` file
- Backend is a Python FastAPI server with two independent subsystems: legacy ML modules and a pipeline system
- Data flows from NBA API → SQLite/Parquet → ML models → REST API → React frontend
- The pipeline subsystem uses a layered collector → processor → feature architecture with resumable progress tracking
- The legacy ML subsystem (`server/ml/`) makes live NBA API calls per-request via `dataset.py` and `prop_line.py`
- Docker Compose orchestrates both services for deployment

## Layers

**Frontend (React SPA):**
- Purpose: User interface for player/team selection, prediction display, and prop line visualization
- Location: `hoopprophet/src/`
- Contains: Single `App.js` component (~590 lines) with embedded theme, API calls, and rendering
- Depends on: Backend REST API (`/players`, `/teams`, `/predict`, `/prop-line`)
- Used by: End users via browser

**API Layer (FastAPI):**
- Purpose: HTTP interface exposing NBA data and ML predictions
- Location: `server/app.py`
- Contains: Pydantic request/response models, CORS middleware, endpoint handlers
- Depends on: `server/ml/` modules for prediction logic, `nba_api` for player/team lookups
- Used by: Frontend via HTTP requests

**Legacy ML Modules:**
- Purpose: On-demand prediction pipeline — trains models per request and returns predictions
- Location: `server/ml/`
- Contains: `dataset.py` (data collection), `prop_line.py` (career averages), `model_train.py` (training & inference)
- Depends on: `nba_api` for live data, `scikit-learn` and `xgboost` for modeling, `google-generativeai` for LLM summaries
- Used by: `server/app.py` via imports

**Data Pipeline:**
- Purpose: Batch collection, storage, and feature engineering for NBA historical data
- Location: `server/pipeline/`
- Contains: Collectors, processors, DB layer, feature pipeline orchestrator
- Depends on: `nba_api` (via `NBAClient`), SQLite, Pandas, Parquet (via PyArrow)
- Used by: CLI runner (`server/pipeline/ingest.py`), tests

**Database Layer:**
- Purpose: Persistent storage for raw NBA data and feature matrices
- Location: `server/pipeline/db/`
- Contains: Schema definition (`schema.py`), connection management (`connection.py`), query functions (`queries.py`)
- Depends on: SQLite (WAL mode)
- Used by: Pipeline collectors, processors, feature pipeline

**Feature Engineering:**
- Purpose: Transform raw game logs into ML-ready feature matrices
- Location: `server/pipeline/processors/`
- Contains: Rolling features, contextual features, matchup features, DNP synthesis, target generation
- Depends on: Feature config (`feature_config.py`), database queries, Pandas
- Used by: Feature pipeline orchestrator (`server/pipeline/features.py`)

## Data Flow

**Real-time Prediction Flow:**

1. User selects player and team in React frontend, clicks "Predict Stats"
2. Frontend sends POST `/predict` with `player_name` and `opponent_team_abv`
3. `server/app.py` `predict_player_stats()` receives request
4. `server/ml/dataset.py` `get_player_id()` resolves player name → ID via NBA API
5. `server/ml/dataset.py` `build_dataset()` fetches game logs, team games, inactive data, rivalry games from NBA API
6. `server/ml/prop_line.py` `get_prop_line()` fetches career averages from NBA API
7. `server/ml/model_train.py` `train_models()` trains Linear Regression and XGBoost per stat with 10×10 RepeatedKFold CV
8. `server/ml/model_train.py` `predict_stats()` generates predictions using the best model per stat
9. `server/ml/model_train.py` `predictions_vs_propline()` compares predictions vs prop lines
10. `server/ml/model_train.py` `generate_model_summary()` calls Gemini API for LLM narrative
11. Response returned as `PredictionResponse` with predictions, prop line comparison, ML metrics, and AI summary
12. Frontend renders prediction results, prop line analysis, and model performance

**Batch Data Pipeline Flow:**

1. CLI runner `server/pipeline/ingest.py` invoked with `--full`, `--refresh`, or `--validate`
2. Seeds players and teams from NBA API static endpoints
3. Collectors run in dependency order:
   - `collect_team_rosters()` → seeds roster associations
   - `collect_team_schedules()` → fetches per-team game schedules
   - `collect_team_stats()` → fetches team advanced stats (DEF_RATING, PACE, etc.)
   - `collect_player_gamelogs()` → fetches per-player per-season game logs
4. `synthesize_all_dnp_rows()` fills in DNP (Did Not Play) rows from roster × schedule gaps
5. If `--features` flag: `run_feature_pipeline()` computes:
   - Rolling averages (L5, L10, L20 windows) and std devs per stat
   - Contextual features (rest days, home/away, opponent defense rating, pace)
   - Matchup features (historical averages vs specific opponent)
   - Target generation (long-format hit/miss lines for each stat type)
6. Feature matrix written to `server/data/features.parquet`

**State Management:**
- Frontend: React `useState` hooks (no external state library)
- Backend-stateless per-request (no session/auth)
- Pipeline: SQLite with `collection_progress` table for resumable collection

## Key Abstractions

**NBAClient (`server/pipeline/nba_client.py`):**
- Purpose: Rate-limited, cached, retry-aware wrapper around `nba_api`
- Examples: `server/pipeline/nba_client.py`
- Pattern: Class-based client with `tenacity` retry decorators on each fetch method, `requests_cache.CachedSession` for HTTP caching, and a 0.6s minimum delay between calls

**Pipeline Collectors:**
- Purpose: Fetch domain-specific data from NBA API and persist to SQLite
- Examples: `server/pipeline/collectors/game_logs.py`, `server/pipeline/collectors/rosters.py`, `server/pipeline/collectors/schedules.py`, `server/pipeline/collectors/team_stats.py`
- Pattern: Each collector function takes `(client: NBAClient, conn: sqlite3.Connection, seasons)` and returns a status dict. Progress tracked via `collection_progress` table for resumability.

**Pipeline Processors:**
- Purpose: Transform raw data into derived features
- Examples: `server/pipeline/processors/rolling_features.py`, `server/pipeline/processors/contextual_features.py`, `server/pipeline/processors/matchup_features.py`, `server/pipeline/processors/target_generator.py`
- Pattern: Pure functions that take a DataFrame and return an enriched DataFrame (except `dnp_synthesis.py` which operates on the DB directly)

**Pydantic Models:**
- Purpose: Request/response validation for FastAPI endpoints
- Examples: `server/app.py` (inline — `PlayerRequest`, `PredictionRequest`, `PlayerResponse`, `PredictionResponse`, `PropLineResponse`, `TeamResponse`)
- Pattern: Pydantic `BaseModel` subclasses defined alongside endpoints

## Entry Points

**Backend API Server:**
- Location: `server/app.py`
- Triggers: `uvicorn app:app --host 0.0.0.0 --port 8000` (or `python -m uvicorn app:app`)
- Responsibilities: Serves REST API endpoints for players, teams, prop lines, predictions, health check

**Pipeline CLI:**
- Location: `server/pipeline/ingest.py`
- Triggers: `python -m server.pipeline.ingest --full/--refresh/--validate/--features-only`
- Responsibilities: Orchestrates all data collection and feature engineering

**Frontend Dev Server:**
- Location: `hoopprophet/src/index.js`
- Triggers: `react-scripts start` (via `npm start`)
- Responsibilities: React app bootstrap, mounts `<App />` component

**Frontend Production:**
- Location: `hoopprophet/Dockerfile`
- Triggers: `npx serve -s build -l 3000`
- Responsibilities: Serves static build artifacts

## Error Handling

**Strategy:** Mixed — endpoints use try/except with HTTPException, pipeline uses logging + progress tracking

**Patterns:**
- FastAPI: Generic `try/except` blocks that catch `Exception` and return `HTTPException(status_code=500)` with error message strings
- Pipeline collectors: Catch exceptions per-entity, mark `collection_progress` as `'failed'` with error message, continue processing other entities
- Pipeline processors: Logging-based error reporting, no explicit error handling for individual row failures
- Frontend: `try/catch` in API calls with status message display to user

**Notable gap:** The `/predict` endpoint does very granular console logging with emojis for each step, suggesting it was built for debugging. Error messages leak to the client (line 252: `detail=f"Error making prediction: {str(e)}"`), which exposes internal implementation details.

## Cross-Cutting Concerns

**Logging:** Python `logging` module in pipeline code (`logger = logging.getLogger(__name__)`), `print()` statements with emojis in `server/app.py` and `server/ml/`. Frontend uses `console.log()`/`console.error()`.

**Validation:** Pydantic models for API request/response validation. Pipeline has `validate_completeness()` function that checks row count thresholds against minimums.

**Authentication:** None — no auth on any endpoint. CORS allows `localhost:3000` and `frontend:3000`.

**Caching:** `requests_cache.CachedSession` with SQLite backend for NBA API calls in `NBAClient`. No application-level caching (predictions are computed fresh per request, including model training).

**Rate Limiting:** `NBAClient` enforces 0.6s minimum delay between calls. `tenacity` retries with exponential backoff (5 attempts, 0.6-30s wait).

---

*Architecture analysis: 2026-04-17*