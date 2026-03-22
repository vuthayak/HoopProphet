# External Integrations

**Analysis Date:** 2025-03-22

## APIs & External Services

**NBA statistics (stats.nba.com via Python client):**
- **nba_api** — Unofficial Python wrapper around NBA Stats HTTP endpoints. Used for:
  - Static player/team lists: `get_players`, `get_teams` (`server/app.py`, `server/ml/dataset.py`, `server/ml/prop_line.py`).
  - Game and career data: `playergamelog`, `teamgamelog`, `commonplayerinfo`, `boxscoresummaryv2`, `playercareerstats` (`server/ml/dataset.py`, `server/ml/prop_line.py`).
- **SDK/Client:** Package `nba_api` (`server/requirements.txt`).
- **Auth:** None for NBA Stats public endpoints (rate limiting and availability depend on NBA infrastructure; `server/ml/dataset.py` uses `time.sleep` between some calls).

**Google Generative AI (Gemini):**
- **Purpose:** Natural-language summaries of cross-validated model metrics after each prediction (`server/ml/model_train.py` — `generate_model_summary()`).
- **SDK/Client:** `google.generativeai` (`import google.generativeai as genai`).
- **Auth:** API key via environment variable **`GEMINI_API_KEY`** (`server/ml/model_train.py`; wired in `docker-compose.yml` from `${GEMINI_API_KEY}`).
- **Model identifier in code:** `genai.GenerativeModel('gemini-2.0-flash-exp')` (`server/ml/model_train.py`). Product marketing in `README.md` references “Gemini 2.5 Flash”; implementers should treat the **code** as the source of truth for the active model name.

**Browser → backend:**
- **Purpose:** SPA loads player/team lists and posts prediction requests.
- **Mechanism:** `fetch()` to `${API_BASE}/players`, `/teams`, `/predict` (`hoopprophet/src/App.js`).
- **Auth:** None (open CORS for configured origins only — see below).

## Data Storage

**Databases:**
- **None** — No SQL/NoSQL client, ORM, or connection string in application code. All data is fetched on demand from NBA APIs and held in memory as pandas objects.

**File Storage:**
- **Local filesystem only** — Optional CSV writes in `server/ml/prop_line.py` `__main__` block (`../data/prop_line.csv`); not part of the FastAPI request path.

**Caching:**
- **None** — No Redis, in-memory cache layer, or CDN integration in code.

## Authentication & Identity

**Auth Provider:**
- **None** — No login, JWT, OAuth, or session handling. The API is intended for local or trusted network use unless extended.

**CORS:**
- **FastAPI `CORSMiddleware`** (`server/app.py`) allows origins `http://localhost:3000` and `http://frontend:3000` with credentials, all methods and headers.

## Monitoring & Observability

**Error Tracking:**
- **None** — No Sentry, Datadog, or similar SDK.

**Logs:**
- **Print statements** — Verbose `print` logging in `server/app.py` (predict flow) and ML modules (`server/ml/model_train.py`, `server/ml/dataset.py`, `server/ml/prop_line.py`).
- **Frontend:** `console.log` / `console.error` in `hoopprophet/src/App.js` for fetch debugging and errors.

## CI/CD & Deployment

**Hosting:**
- **Docker Compose** — Local/dev-style orchestration (`docker-compose.yml`). No cloud provider manifest in-repo.

**CI Pipeline:**
- **Not detected** — No `.github/workflows/` or similar CI configuration in the repository.

## Environment Configuration

**Required env vars (for full functionality):**
- **`GEMINI_API_KEY`** — Required for non-placeholder AI summaries in `generate_model_summary()`; if unset, API still runs but returns a string stating the key is missing (`server/ml/model_train.py`).

**Optional / deployment-specific:**
- **`REACT_APP_API_BASE`** — Backend origin for the React app (`hoopprophet/src/App.js`). Defaults to `http://localhost:8000` when unset.

**Secrets location:**
- **`.env` at project root** — Documented in `README.md` for `GEMINI_API_KEY`; file should remain untracked (see `README.md` / `.gitignore` patterns). Never commit secret values.

## Webhooks & Callbacks

**Incoming:**
- **None** — No Stripe webhooks, GitHub hooks, or similar HTTP callback endpoints.

**Outgoing:**
- **None** — No registered webhooks to third parties. The app only performs request/response calls: browser → FastAPI, FastAPI → NBA Stats (via `nba_api`), FastAPI → Gemini API.

---

*Integration audit: 2025-03-22*
