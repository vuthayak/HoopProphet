# Technology Stack

**Analysis Date:** 2026-04-17

## Languages

**Primary:**
- Python 3.11 — Backend API, ML pipeline, data processing (`server/`)
- JavaScript (ES6+) — Frontend React single-page application (`hoopprophet/src/`)

**Secondary:**
- SQL (SQLite dialect) — Database schema definition (`server/pipeline/db/schema.py`)
- YAML — Docker Compose orchestration (`docker-compose.yml`)
- HTML — SPA shell (`hoopprophet/public/index.html`)

## Runtime

**Environment:**
- Python 3.11-slim (Docker backend base image) — `server/Dockerfile`
- Node.js 20 Alpine (Docker frontend base image) — `hoopprophet/Dockerfile`

**Package Managers:**
- pip — Python dependencies (`server/requirements.txt`)
- npm — JavaScript dependencies (`hoopprophet/package.json`, `hoopprophet/package-lock.json`)
- Lockfile: `hoopprophet/package-lock.json` present

## Frameworks

**Core:**
- FastAPI — Python async web framework serving the backend API (`server/app.py`)
- React 19.1.0 — Frontend UI library (`hoopprophet/src/App.js`)
- Material-UI (MUI) 7.2.0 — React component library for UI (`hoopprophet/src/App.js`)
- uvicorn — ASGI server for FastAPI (`server/Dockerfile`, `server/app.py`)

**Machine Learning:**
- scikit-learn — sklearn pipelines, cross-validation, StandardScaler, LinearRegression (`server/ml/model_train.py`)
- XGBoost — XGBRegressor for prediction models (`server/ml/model_train.py`)
- pandas 2.2+ / numpy 2.1+ — Data manipulation throughout backend (`server/ml/dataset.py`, `server/pipeline/features.py`)
- pyarrow 19+ — Parquet file I/O for feature matrix (`server/pipeline/features.py`)

**Testing:**
- pytest 8+ — Python test framework (`pyproject.toml`, `server/tests/`)
- pytest-timeout 2.2+ — Test timeout enforcement (`pyproject.toml`)
- React Testing Library — Frontend component testing (`hoopprophet/package.json`)

**Build/Dev:**
- react-scripts 5.0.1 — CRA build toolchain (`hoopprophet/package.json`)
- Docker Compose 3.9 — Multi-container orchestration (`docker-compose.yml`)

## Key Dependencies

**Critical:**
- nba_api 1.11.4 — Official NBA stats API wrapper; primary data source for all player/team/game data (`server/requirements.txt`, `server/ml/dataset.py`, `server/pipeline/nba_client.py`)
- google-generativeai — Google Gemini 2.0 Flash API for AI-powered model summaries (`server/ml/model_train.py`)
- requests-cache 1.3.1 — HTTP response caching for NBA API calls (`server/pipeline/nba_client.py`)
- tenacity 9+ — Retry logic with exponential backoff for NBA API calls (`server/pipeline/nba_client.py`)
- tqdm 4.66+ — Progress bars for long-running collection processes (`server/requirements.txt`)

**Infrastructure:**
- Pydantic — Request/response models and validation in FastAPI (`server/app.py`)
- SQLite (stdlib) — Local database for data pipeline storage (`server/pipeline/db/connection.py`)
- framer-motion 12.23+ — Animation library for React UI transitions (`hoopprophet/src/App.js`)

## Configuration

**Environment:**
- `GEMINI_API_KEY` — Required for AI model summary generation; set via `.env` file or Docker env (`server/ml/model_train.py`, `docker-compose.yml`)
- `REACT_APP_API_BASE` — Backend API base URL for frontend; defaults to `http://localhost:8000`, set to `http://backend:8000` in Docker (`hoopprophet/src/App.js`, `docker-compose.yml`)

**Build:**
- `hoopprophet/package.json` — Frontend dependency config with ESLint (react-app preset) and proxy setting
- `server/requirements.txt` — Python pinned/minimum versions
- `pyproject.toml` — pytest config (testpaths, timeout)
- `docker-compose.yml` — Multi-service orchestration (backend:8000, frontend:3000)

## Platform Requirements

**Development:**
- Python 3.11+ with pip
- Node.js 20+ with npm
- Docker Desktop (for containerized dev)
- Gemini API key for AI summary feature

**Production:**
- Docker Compose orchestrates both services
- Backend exposed on port 8000 (FastAPI/Uvicorn)
- Frontend served via `npx serve` on port 3000 (static React build)
- SQLite database persisted in `server/data/hoopprophet.db`
- HTTP cache for NBA API stored in `server/data/nba_cache`
- Feature matrix Parquet file in `server/data/features.parquet`

---

*Stack analysis: 2026-04-17*