# Codebase Structure

**Analysis Date:** 2025-03-22

## Directory Layout

```
HoopProphet/
├── README.md                 # Project overview and Docker quick start
├── docker-compose.yml        # frontend :3000, backend :8000, env wiring
├── .gitignore                # Root ignore rules
├── server/                   # FastAPI backend + ML package
│   ├── Dockerfile            # Python 3.11, uvicorn on 8000
│   ├── app.py                # FastAPI app, routes, Pydantic models
│   ├── requirements.txt      # Python dependencies
│   └── ml/                   # Dataset, training, prop lines
│       ├── dataset.py        # Feature build from NBA game logs
│       ├── model_train.py      # CV, predict, Gemini summary
│       └── prop_line.py      # Career averages / prop lines
└── hoopprophet/              # Create React App–style frontend
    ├── Dockerfile            # build + serve static on 3000
    ├── package.json
    ├── package-lock.json
    ├── README.md
    ├── .gitignore
    ├── public/
    │   └── index.html        # HTML shell, root div
    └── src/
        ├── index.js          # ReactDOM root → App
        ├── App.js            # Entire UI + API client logic
        └── assets/
            └── hoopprophet-logo.svg
```

## Directory Purposes

**`server/`:**
- Purpose: HTTP API and all Python ML/data code.
- Contains: Single-module FastAPI app (`app.py`), dependency list (`requirements.txt`), container build (`Dockerfile`), package `ml/`.
- Key files: `server/app.py`, `server/ml/dataset.py`, `server/ml/model_train.py`, `server/ml/prop_line.py`

**`server/ml/`:**
- Purpose: Isolated ML and NBA data-ingestion logic imported as `ml.*` from `app.py` (working directory `/app` in Docker exposes `app` next to `ml`).
- Contains: Pandas/sklearn/xgboost pipelines; no `__init__.py` required for namespace if Python path includes `server` (imports use `from ml.`).
- Key files: `dataset.py`, `model_train.py`, `prop_line.py`

**`hoopprophet/`:**
- Purpose: React UI only; no shared code with backend.
- Contains: SPA entry, single large component, static public assets, npm lockfile.
- Key files: `hoopprophet/src/App.js`, `hoopprophet/src/index.js`, `hoopprophet/public/index.html`

**Repository root:**
- Purpose: Compose orchestration and top-level documentation.
- Contains: `docker-compose.yml`, `README.md`

## Key File Locations

**Entry Points:**
- `hoopprophet/src/index.js`: React bootstrap; mounts `App`.
- `hoopprophet/public/index.html`: `#root` mount point.
- `server/app.py`: `FastAPI` instance and `uvicorn` dev entry in `if __name__ == "__main__"`.

**Configuration:**
- `docker-compose.yml`: Service names, ports, `GEMINI_API_KEY`, `REACT_APP_API_BASE`.
- `server/requirements.txt`: Backend Python packages.
- `hoopprophet/package.json`: React scripts and dependencies (MUI, framer-motion, etc.).
- `.env` at project root (documented in `README.md`) — **not** read by tools; supplies `GEMINI_API_KEY` to Compose.

**Core Logic:**
- `server/app.py`: REST endpoints and orchestration.
- `server/ml/dataset.py`: `build_dataset` and helpers.
- `server/ml/model_train.py`: Training, prediction, Gemini summary.
- `server/ml/prop_line.py`: Career prop lines and `get_player_id`.
- `hoopprophet/src/App.js`: UI, `API_BASE`, fetch logic.

**Testing:**
- Not detected — no `*.test.*`, `*.spec.*`, or test config files in the repo.

## Naming Conventions

**Files:**
- React: `PascalCase` for main component (`App.js`), `index.js` for entry.
- Python: `snake_case` modules (`app.py`, `dataset.py`, `model_train.py`, `prop_line.py`).

**Directories:**
- Lowercase: `server`, `ml`, `hoopprophet`, `src`, `public`, `assets`.

**Symbols:**
- React component: `App` (default export from `App.js`).
- FastAPI: `app` instance; route functions `snake_case` (`get_active_players`, `predict_player_stats`).
- Python functions: `snake_case` (`build_dataset`, `train_models`).

## Where to Add New Code

**New Feature (e.g., additional stat or endpoint):**
- Primary API changes: `server/app.py` (new routes and Pydantic models).
- ML changes: extend `server/ml/dataset.py` (features), `server/ml/model_train.py` (stat list / pipelines), and optionally `server/ml/prop_line.py` if prop line columns change.
- Frontend: extend `hoopprophet/src/App.js` or split into new files under `hoopprophet/src/` and import from `App.js`.

**New Component/Module (frontend):**
- Implementation: Prefer `hoopprophet/src/components/<Name>.js` (pattern to adopt — **not** present yet) and import into `App.js` to keep `App.js` maintainable.

**Utilities:**
- Shared React helpers: `hoopprophet/src/utils/` or colocated in new modules (convention to establish when first needed).
- Shared Python helpers: new module under `server/ml/` or `server/` if not ML-specific.

**Tests (if introduced):**
- Co-locate or use `server/tests/` and `hoopprophet/src/**/*.test.js` — **no structure exists**; choose Jest/React Testing Library and `pytest` to match common CRA and FastAPI practice.

## Special Directories

**`hoopprophet/build/` (after `npm run build`):**
- Purpose: Production static output consumed by `npx serve` in Docker.
- Generated: Yes (by `npm run build` in `hoopprophet/Dockerfile`).
- Committed: No — typically gitignored via CRA defaults (`hoopprophet/.gitignore`).

**`node_modules/`:**
- Purpose: npm dependencies.
- Generated: Yes.
- Committed: No.

**`.planning/codebase/`:**
- Purpose: GSD architecture and mapping artifacts for agents and planners.
- Generated: By mapping workflow.
- Committed: Per team preference (often yes for shared context).

---

*Structure analysis: 2025-03-22*
