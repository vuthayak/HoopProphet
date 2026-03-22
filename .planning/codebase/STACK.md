# Technology Stack

**Analysis Date:** 2025-03-22

## Languages

**Primary:**
- **JavaScript (ES modules / JSX)** — React UI in `hoopprophet/src/` (`App.js`, `index.js`).
- **Python 3.11** — FastAPI API and ML pipeline in `server/` (`app.py`, `server/ml/`).

**Secondary:**
- **CSS-in-JS** — Emotion + MUI `sx` styling in `hoopprophet/src/App.js` (no separate CSS preprocessor detected).

## Runtime

**Environment:**
- **Node.js 20** — Declared by `hoopprophet/Dockerfile` (`FROM node:20-alpine`).
- **Python 3.11** — Declared by `server/Dockerfile` (`FROM python:3.11-slim`).

**Package Manager:**
- **npm** — Frontend; lockfile present at `hoopprophet/package-lock.json`.
- **pip** — Backend; `server/requirements.txt` lists dependencies **without pinned versions** (installs latest compatible at install time).

## Frameworks

**Core:**
- **React 19.x** — UI (`hoopprophet/package.json`: `react`, `react-dom`).
- **Create React App / react-scripts 5.0.1** — Dev server, build, and Jest test runner (`hoopprophet/package.json` scripts: `start`, `build`, `test`).
- **FastAPI** — HTTP API (`server/app.py`).
- **Uvicorn** — ASGI server for FastAPI (`server/Dockerfile` `CMD`, `server/app.py` `__main__` block).
- **Pydantic v2** (via FastAPI) — Request/response models in `server/app.py` (`BaseModel`).

**UI / UX:**
- **Material UI (MUI) 7.x** — Components and theming (`hoopprophet/package.json`: `@mui/material`, `@mui/icons-material`).
- **Emotion 11.x** — CSS-in-JS peer for MUI (`@emotion/react`, `@emotion/styled`).
- **Framer Motion 12.x** — Animation (`hoopprophet/src/App.js`).

**ML / Data:**
- **pandas** — DataFrames throughout `server/ml/` and `server/app.py`.
- **NumPy** — Used in `server/ml/dataset.py` (imported alongside pandas).
- **scikit-learn** — Pipelines, `LinearRegression`, `RepeatedKFold`, `cross_val_score`, `StandardScaler` (`server/ml/model_train.py`).
- **XGBoost** — `XGBRegressor` in `server/ml/model_train.py`.
- **nba_api** — Python client for NBA Stats endpoints (`server/ml/dataset.py`, `server/ml/prop_line.py`, `server/app.py`).

**AI:**
- **google-generativeai** — Gemini API client (`server/ml/model_train.py`: `import google.generativeai as genai`).

**Testing:**
- **Jest** (via `react-scripts test`) — `hoopprophet/package.json` script `test`.
- **React Testing Library** — `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `@testing-library/dom` in `hoopprophet/package.json`.

**Build / Dev:**
- **Production static serve** — `hoopprophet/Dockerfile` runs `npm run build` then `npx serve -s build -l 3000` (the `serve` package is invoked via `npx`, not listed in `hoopprophet/package.json`).
- **Docker Compose 3.9** — Orchestration (`docker-compose.yml`).

## Key Dependencies

**Critical:**
- `fastapi` + `uvicorn` — API surface and process model (`server/app.py`).
- `nba_api` — All live/static NBA data used for players, teams, game logs, career stats (`server/ml/dataset.py`, `server/ml/prop_line.py`, `server/app.py`).
- `pandas` — Shared data layer between API and ML.
- `scikit-learn`, `xgboost` — Training and prediction in `server/ml/model_train.py`.
- `google-generativeai` — Natural-language model summaries in `generate_model_summary()` (`server/ml/model_train.py`).

**Infrastructure:**
- `react`, `react-dom`, `react-scripts` — SPA shell and toolchain (`hoopprophet/`).
- `@mui/material`, `@emotion/react`, `@emotion/styled` — UI system (`hoopprophet/src/App.js`).

## Configuration

**Environment:**
- **Backend:** `GEMINI_API_KEY` read in `server/ml/model_train.py` (`os.getenv('GEMINI_API_KEY')`). Passed through `docker-compose.yml` from host environment (`.env` at project root is documented in `README.md`; do not commit secrets).
- **Frontend:** `REACT_APP_API_BASE` — Base URL for API calls (`hoopprophet/src/App.js`: `process.env.REACT_APP_API_BASE || "http://localhost:8000"`). Set in `docker-compose.yml` for the `frontend` service as `http://backend:8000`.
- **Development proxy:** `hoopprophet/package.json` sets `"proxy": "http://backend:8000"` for CRA dev server when using Docker service names (local dev typically uses `REACT_APP_API_BASE` or localhost as documented in `README.md`).

**Build:**
- **Frontend:** CRA defaults; entry `hoopprophet/src/index.js`, HTML shell `hoopprophet/public/index.html`.
- **Backend:** `server/Dockerfile` copies `requirements.txt` then application tree; no `pyproject.toml` or pinned transitive lockfile.
- **Compose:** `docker-compose.yml` — builds `server` and `hoopprophet` images, maps ports `8000` (backend) and `3000` (frontend).

## Platform Requirements

**Development:**
- **Docker** and **Docker Compose** — Primary path in `README.md` (`docker-compose up --build`).
- **Alternative:** Local Node + npm in `hoopprophet/`; Python venv + `pip install -r server/requirements.txt` + `uvicorn` in `server/` (`README.md`).

**Production:**
- **Containerized** — Two images (Python API + Node build served as static files). No separate production hosting config (e.g. Kubernetes, serverless) in-repo; targets are the Dockerized Node 20 and Python 3.11 images above.

---

*Stack analysis: 2025-03-22*
