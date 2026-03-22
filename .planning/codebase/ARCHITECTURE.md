# Architecture

**Analysis Date:** 2025-03-22

## Pattern Overview

**Overall:** Full-stack **client–server** architecture with a **React single-page application** calling a **FastAPI REST API**. Machine learning and data ingestion run **synchronously inside the request path** for the main prediction flow (no separate job queue or ML service).

**Key Characteristics:**
- **Thin API layer:** `server/app.py` maps HTTP routes to Pydantic models and delegates to `server/ml/` modules.
- **Monolithic frontend:** All UI, state, and API calls live in one component (`hoopprophet/src/App.js`).
- **NBA data at the edge:** The backend pulls live/static data via `nba_api` (stats endpoints and static player/team lists).
- **Optional LLM enrichment:** `generate_model_summary` in `server/ml/model_train.py` calls Google Gemini when `GEMINI_API_KEY` is set (also injected via `docker-compose.yml`).

## Layers

**Presentation (React SPA):**
- Purpose: Player/team selection, trigger prediction, render numeric predictions, prop-line comparison strings, and Gemini narrative.
- Location: `hoopprophet/src/`
- Contains: React 18 bootstrap (`index.js`), single `App` component with MUI theme and Framer Motion (`App.js`), static assets (`assets/`), HTML shell (`public/index.html`).
- Depends on: Backend HTTP API (`fetch` to `API_BASE`); CDN images from `cdn.nba.com` for headshots and logos.
- Used by: Browser users; served in Docker by static build + `serve` (`hoopprophet/Dockerfile`).

**HTTP API (FastAPI):**
- Purpose: CORS-enabled REST endpoints for players, teams, player/team lookup, prop lines, predictions, and health.
- Location: `server/app.py`
- Contains: `FastAPI` app, `CORSMiddleware`, Pydantic request/response models (`PlayerRequest`, `PredictionResponse`, etc.), route handlers.
- Depends on: `nba_api.stats.static` for `/players`, `/teams`, `/player/{player_name}`, `/team/{team_name}`; `server/ml` for `/prop-line` and `/predict`.
- Used by: `hoopprophet/src/App.js` (and OpenAPI docs at `/docs` when backend runs).

**ML & data pipeline (Python modules):**
- Purpose: Build per-player feature tables from game logs, compute career “prop line” baselines, cross-validate Linear Regression vs XGBoost per stat, predict next-game stats, compare to prop lines, optionally summarize metrics with Gemini.
- Location: `server/ml/`
- Contains:
  - `dataset.py` — `build_dataset`, season helpers, merge of player/team logs, inactive-game detection, rivalry games, `dataset_cleaning` feature engineering.
  - `prop_line.py` — `get_player_id`, `get_prop_line` (career per-game averages, halved rounding for lines).
  - `model_train.py` — `train_models`, `predict_stats`, `predictions_vs_propline`, `generate_model_summary` (Gemini).
- Depends on: `nba_api`, `pandas`, `sklearn`, `xgboost`, `google.generativeai` (for summaries).
- Used by: `server/app.py` imports (`from ml.prop_line import ...`, `from ml.dataset import ...`, `from ml.model_train import ...`).

**Container / runtime:**
- Purpose: Run backend on port 8000 and frontend on 3000 with shared env for Gemini.
- Location: `docker-compose.yml`, `server/Dockerfile`, `hoopprophet/Dockerfile`
- Contains: Backend bind-mount of `./server` for dev-style live code; `REACT_APP_API_BASE=http://backend:8000` for browser-to-API resolution inside Compose network.

## Data Flow

**Bootstrap (page load):**

1. `App` mounts; `useEffect` runs `Promise.all` fetching `GET ${API_BASE}/players` and `GET ${API_BASE}/teams`.
2. JSON arrays populate `players` and `teams` state for MUI `Autocomplete` widgets.

**Prediction (`POST /predict`):**

1. User selects `full_name` and team `abbreviation`; `handlePredict` posts JSON `{ player_name, opponent_team_abv }` to `POST ${API_BASE}/predict` (`hoopprophet/src/App.js`).
2. `predict_player_stats` in `server/app.py` resolves `player_id` via `get_player_id` from `ml.prop_line`.
3. `build_dataset(player_name, opponent_team_abv)` (`server/ml/dataset.py`) loads game logs, merges team context, flags inactive/DND rows, appends rivalry games, returns cleaned `DataFrame`.
4. `get_prop_line(player_id)` (`server/ml/prop_line.py`) fetches career averages as a one-row baseline for comparison.
5. `train_models(data)` (`server/ml/model_train.py`) runs repeated k-fold CV for each stat, chooses Linear Regression or XGBoost (or falls back to mean when R² &lt; 0).
6. `predict_stats(data, metrics_df)` fits the chosen pipeline on full data and predicts from the **last row** of features for each stat.
7. `predictions_vs_propline(predictions, prop_line)` builds human-readable OVER/UNDER strings vs career prop values (special case for triple/double-double).
8. `generate_model_summary(metrics_df)` may call Gemini and return narrative text (or a fallback string if the key is missing or an error occurs).
9. Response JSON includes `predictions`, `vs_prop_line`, `ml_metrics`, `model_summary`; the UI binds `predictions`, `vs_prop_line`, and `model_summary` in `App.js` (numeric grid, prop analysis panel, model summary panel). **`ml_metrics` is returned by the API but not rendered in the current UI.**

**Simpler flows:**
- `POST /prop-line`: `get_player_id` → `get_prop_line` → serialize `prop_lines` (`server/app.py`).
- Static lists: `get_players()` / `get_teams()` from `nba_api` inside route handlers (`server/app.py`).

**State Management:**
- Client: React `useState` only (no Redux, no React Query) in `hoopprophet/src/App.js`.
- Server: Stateless between requests; no application database — all data from `nba_api` and in-memory DataFrames per request.

## Key Abstractions

**`build_dataset` (`server/ml/dataset.py`):**
- Purpose: End-to-end feature matrix for one player + opponent context.
- Examples: `build_dataset` orchestrates `get_team_games`, `get_player_gamelog`, `player_inactive`, `get_rivalry_games`, `dataset_cleaning`.
- Pattern: Imperative pandas pipeline with NBA API I/O and rolling windows.

**Prop line baseline (`server/ml/prop_line.py`):**
- Purpose: Career per-game averages (selected columns), rounded to half-points for betting-style lines.
- Examples: `get_prop_line`, `get_player_id`.
- Pattern: Single-row `DataFrame` aligned with prediction stat keys for `predictions_vs_propline`.

**Model selection & prediction (`server/ml/model_train.py`):**
- Purpose: Per-stat model choice via CV R²; prediction uses full-data refit on latest row.
- Examples: `train_models`, `predict_stats`, `predictions_vs_propline`, `generate_model_summary`.
- Pattern: `sklearn.pipeline.Pipeline` with `StandardScaler` + `LinearRegression` or `XGBRegressor`; `RepeatedKFold` for scoring.

**HTTP contracts (`server/app.py`):**
- Purpose: Typed JSON I/O.
- Examples: `PredictionRequest`, `PredictionResponse` — keep client and server aligned with `hoopprophet/src/App.js` POST body and response usage.

**Duplicate helper:** `get_player_id` is implemented in both `server/ml/dataset.py` and `server/ml/prop_line.py` with the same behavior; `app.py` imports from `prop_line` for prediction.

## Entry Points

**Browser UI:**
- Location: `hoopprophet/src/index.js`
- Triggers: Page load.
- Responsibilities: Mount `App` under `React.StrictMode`.

**React application root:**
- Location: `hoopprophet/src/App.js`
- Triggers: Rendered by `index.js`.
- Responsibilities: Theme, layout, data fetch, `POST /predict`, results sections.

**FastAPI application:**
- Location: `server/app.py` (`app = FastAPI(...)`)
- Triggers: Uvicorn (`CMD` in `server/Dockerfile`, or `python app.py` / `uvicorn` in `if __name__ == "__main__"` block).
- Responsibilities: Route registration, CORS, orchestration of ML steps for `/predict`.

**Docker Compose:**
- Location: `docker-compose.yml`
- Triggers: `docker compose up`
- Responsibilities: Build/run `backend` and `frontend`, pass `GEMINI_API_KEY`, set `REACT_APP_API_BASE` for frontend build/runtime.

## Error Handling

**Strategy:** Route-level `try`/`except` with `HTTPException(500, detail=...)` for most failures; re-raise `HTTPException` for 404 paths (`server/app.py`). ML/Gemini errors in `generate_model_summary` return error strings rather than failing the whole request.

**Patterns:**
- API: `raise HTTPException(status_code=404, ...)` when player/team row missing; generic 500 with exception message for others.
- Client: `fetch` failure sets `predictionStatus` user message; does not use an error boundary.
- `dataset.py` / inactive loop: per-game `try`/`except` with `continue` on box score errors.

## Cross-Cutting Concerns

**Logging:** `print` statements in `server/app.py` (`/predict` path) and print/debug in ML modules — no structured logging framework.

**Validation:** Pydantic models on request bodies (`server/app.py`); path/query params typed by FastAPI.

**Authentication:** Not implemented — public API (appropriate only for local/dev unless fronted by auth layer).

---

*Architecture analysis: 2025-03-22*
