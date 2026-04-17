# External Integrations

**Analysis Date:** 2026-04-17

## APIs & External Services

**NBA Stats API:**
- nba_api (Python package v1.11.4) — Primary data source for all NBA player, team, game, and schedule data
  - SDK: `nba_api` (`server/requirements.txt`)
  - Auth: None required (public API)
  - Usage areas:
    - Player search and info: `nba_api.stats.static.players.get_players()` (`server/app.py`, `server/ml/dataset.py`, `server/ml/prop_line.py`)
    - Team search and info: `nba_api.stats.static.teams.get_teams()` (`server/app.py`, `server/pipeline/nba_client.py`)
    - Player game logs: `nba_api.stats.endpoints.playergamelog` (`server/ml/dataset.py`, `server/pipeline/nba_client.py`)
    - Player career stats: `nba_api.stats.endpoints.playercareerstats` (`server/ml/prop_line.py`)
    - Common player info: `nba_api.stats.endpoints.commonplayerinfo` (`server/ml/dataset.py`)
    - Box score summaries: `nba_api.stats.endpoints.boxscoresummaryv2` (`server/ml/dataset.py`)
    - Team game logs: `nba_api.stats.endpoints.teamgamelog` (`server/ml/dataset.py`)
    - Team rosters: `nba_api.stats.endpoints.commonteamroster` (`server/pipeline/nba_client.py`)
    - Team schedules: `nba_api.stats.endpoints.leaguegamefinder` (`server/pipeline/nba_client.py`)
    - Team advanced stats: `nba_api.stats.endpoints.leaguedashteamstats` (`server/pipeline/nba_client.py`)
  - Rate limiting: Built-in 0.6s minimum delay + exponential backoff retry (5 attempts) in `NBAClient` class (`server/pipeline/nba_client.py`)
  - Caching: `requests-cache` with SQLite backend, stale-if-error policy (`server/pipeline/nba_client.py`)

**Google Generative AI (Gemini):**
- Gemini 2.0 Flash Exp — AI-generated model performance summaries after predictions
  - SDK: `google-generativeai` (`server/requirements.txt`)
  - Auth: `GEMINI_API_KEY` environment variable (`server/ml/model_train.py`)
  - Model: `gemini-2.0-flash-exp` (hardcoded in `generate_model_summary()`)
  - Usage: Generates 150-word betting perspective analysis of ML model metrics
  - Graceful degradation: Returns "Model summary unavailable" message if API key not set

**CDN — NBA Headshots & Logos:**
- Player headshots: `https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png` (`hoopprophet/src/App.js`)
- Team logos: `https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg` (`hoopprophet/src/App.js`)
- Auth: None (public CDN)

**Google Fonts:**
- "Special Gothic Expanded One" — Display font loaded via Google Fonts CSS API (`hoopprophet/public/index.html`)

## Data Storage

**Databases:**
- SQLite — Local file-based relational database
  - Connection: File path `server/data/hoopprophet.db` (`server/pipeline/__init__.py`)
  - Client: Python stdlib `sqlite3` module (`server/pipeline/db/connection.py`)
  - Mode: WAL journal mode, foreign keys enabled
  - Tables: `players`, `teams`, `player_game_logs`, `team_stats`, `team_rosters`, `team_schedules`, `collection_progress`
  - Schema defined in: `server/pipeline/db/schema.py`

**File Storage:**
- Parquet feature matrix: `server/data/features.parquet` — Pre-computed ML feature store written by `server/pipeline/features.py`
- HTTP cache: `server/data/nba_cache` — SQLite-based HTTP response cache for NBA API
- Gitkeep: `server/data/.gitkeep` — Ensures data directory is tracked

**Caching:**
- requests-cache — SQLite-backed HTTP cache for NBA API responses (`server/pipeline/nba_client.py`)
  - Backend: SQLite
  - Policy: No expiration (`expire_after=None`), stale-if-error
  - Allowable methods: GET, POST
  - Session injected into `NBAStatsHTTP` for transparent caching

## Authentication & Identity

**Auth Provider:**
- None — The application has no user authentication. All API endpoints are publicly accessible.

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logs:**
- Python `logging` module — Structured logging in pipeline module (`server/pipeline/nba_client.py`, `server/pipeline/ingest.py`)
- Console print statements — Debug logging in `server/app.py` and `server/ml/model_train.py` (emoji-prefixed step indicators)
- Frontend: `console.log` / `console.error` — Browser console logging (`hoopprophet/src/App.js`)

## CI/CD & Deployment

**Hosting:**
- Docker Compose — Local multi-container deployment
  - Backend: Python 3.11-slim container, uvicorn serving FastAPI on port 8000
  - Frontend: Node 20 Alpine container, static build served via `npx serve` on port 3000
  - Backend volume mount: `./server:/app` for hot-reload development

**CI Pipeline:**
- None configured

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY` — Google Gemini API key for AI model summaries (required for /predict endpoint AI summary)
- `REACT_APP_API_BASE` — Backend URL for frontend API calls (defaults to `http://localhost:8000`)

**Secrets location:**
- `.env` file at project root (gitignored) — Contains `GEMINI_API_KEY`
- Docker Compose passes `GEMINI_API_KEY` and `REACT_APP_API_BASE` to containers

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-04-17*