# Coding Conventions

**Analysis Date:** 2026-03-22

## Naming Patterns

**Files (frontend):**
- React entry and root component use `PascalCase` filenames: `App.js`, not `app.js`.
- Asset paths use lowercase with hyphens where applicable: `hoopprophet/src/assets/hoopprophet-logo.svg`.

**Files (backend):**
- Python modules use `snake_case`: `app.py`, `prop_line.py`, `model_train.py`, `dataset.py`.

**Functions:**
- **JavaScript:** `camelCase` for handlers and helpers (`handlePredict`, `prettifyStatName`, `fetchData`).
- **Python:** `snake_case` for module-level functions (`get_player_id`, `build_dataset`, `train_models`, `predict_stats`).

**Variables:**
- **React state:** `camelCase` (`selectedPlayer`, `predictionStatus`, `loading`).
- **Python:** `snake_case` (`player_id`, `metrics_df`, `active_players`). Pydantic model fields use `snake_case` aligned with JSON/API bodies (`player_name`, `opponent_team_abv`).

**Types:**
- **Python API:** Pydantic `BaseModel` classes use `PascalCase` (`PredictionRequest`, `TeamResponse`). Type hints use `List`, `Dict`, `Optional` from `typing` in `server/app.py`.
- **JavaScript:** No TypeScript; prop shapes follow NBA API / backend response objects (e.g. `full_name`, `abbreviation` on autocomplete options).

## Code Style

**Formatting:**
- **Frontend:** No standalone Prettier config in the repo; formatting is effectively CRA + ESLint defaults. `hoopprophet/package.json` embeds `eslintConfig` only (no `.prettierrc`).
- **Backend:** Standard Python layout; spacing around operators is inconsistent in places (e.g. `== True` vs `== True` with spaces in `server/ml/prop_line.py`).

**Linting:**
- **Frontend:** ESLint via `eslintConfig` in `hoopprophet/package.json` extending `react-app` and `react-app/jest`.
- **Python:** Not detected (no `ruff`, `flake8`, `pylint`, or `pyproject.toml` tool config in the explored tree).

## Import Organization

**Order (observed in `server/app.py`):**
1. Third-party framework imports (`fastapi`, `pydantic`, `pandas`, `typing`).
2. Local package imports (`ml.*`, `nba_api.*`).

**Order (observed in `hoopprophet/src/App.js`):**
1. `react` hooks.
2. Static assets (`./assets/...`).
3. Third-party UI/animation (`framer-motion`, `@mui/material`).
4. No path aliases; imports are relative (`./App` from `index.js`).

**Path Aliases:**
- Not used. Default CRA resolution only.

## Error Handling

**Frontend (`hoopprophet/src/App.js`):**
- `fetch` paths use `try/catch`; failures log with `console.error` and update UI state (`setLoading(false)`, user-facing `predictionStatus` on predict failures).
- HTTP errors: `if (!response.ok) throw new Error('Prediction...')` then caught in the same `catch` block.
- Image load failures: `onError={e => (e.target.style.display = 'none')}` hides broken NBA CDN images.

**Backend (`server/app.py`):**
- Route handlers wrap logic in `try/except`.
- **404:** `HTTPException(status_code=404, detail="...")` when a player/team row is missing.
- **500:** Generic `except Exception as e:` → `HTTPException(status_code=500, detail=f"Error ...: {str(e)}")`.
- **Re-raise:** `except HTTPException: raise` so FastAPI HTTP errors are not converted to 500 (see `get_team_info`, `get_player_info`).
- **`/predict`:** On failure, prints traceback to stdout then raises `HTTPException(500, ...)`.

**Python ML (`server/ml/model_train.py`):**
- `generate_model_summary` uses `try/except` and returns a user-visible string on missing API key or Gemini errors instead of raising.

## Logging

**Framework:** Primarily `print` in Python (`server/app.py`, `server/ml/*.py`); `console.log` / `console.error` in the React app.

**Patterns:**
- Predict endpoint uses step-style logging with emoji prefixes (e.g. "Step 1", success/error markers).
- `server/ml/dataset.py` prints progress messages ("Seasons Retrieved", "Player game log retrieved").
- Frontend includes debug `console.log` for selected player/team and initial fetch samples—treat as development noise; remove or gate for production if tightening conventions.

## Comments

**When to Comment:**
- JSX uses `{/* ... */}` for section labels (e.g. `{/* Player Selection */}`) in `hoopprophet/src/App.js`.
- Python modules use `# Function to ...` style comments above helpers in `server/ml/dataset.py`.

**JSDoc/TSDoc:**
- Not used (JavaScript-only frontend).

**Python docstrings:**
- Mixed styles: `get_prop_line` in `server/ml/prop_line.py` uses **Args/Returns** blocks; `load_data`, `predict_stats`, `build_dataset` in `server/ml/model_train.py` / `server/ml/dataset.py` use **Parameters/Returns** prose. New code should pick one style (prefer consistent Google or NumPy style across `server/ml/`).

## Function Design

**Size:**
- `App` in `hoopprophet/src/App.js` is a single large component (~590 lines). Conventional split would be subcomponents under e.g. `hoopprophet/src/components/`—not present yet.

**Parameters:**
- FastAPI dependencies use typed path/query/body models; ML functions take primitives and `pd.DataFrame` without exhaustive type hints on every parameter.

**Return Values:**
- API responses use Pydantic models or `response_model=List[dict]` for list endpoints.
- ML helpers return `pd.DataFrame`, `dict`, or scalars as appropriate.

## Module Design

**Exports:**
- React: `export default App` in `hoopprophet/src/App.js`.
- Python: implicit module functions; relative imports inside package (`from .dataset import build_dataset` in `server/ml/model_train.py`).

**Barrel Files:**
- Not used in the frontend (`index.js` only bootstraps React).

## Environment and Configuration

**Frontend:** `process.env.REACT_APP_API_BASE` with fallback `"http://localhost:8000"` in `hoopprophet/src/App.js`. CRA docs apply for naming (`REACT_APP_*`).

**Backend:** `GEMINI_API_KEY` read in `server/ml/model_train.py` for Gemini; absence returns a string placeholder instead of failing the request.

**Git ignore:** Root `.gitignore` lists `.env`. `hoopprophet/.gitignore` ignores `.env.local`, `.env.development.local`, `.env.test.local`, `.env.production.local` and `/coverage`.

---

*Convention analysis: 2026-03-22*
