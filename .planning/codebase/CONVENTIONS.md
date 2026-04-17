# Coding Conventions

**Analysis Date:** 2026-04-17

## Project Overview

HoopProphet is a monorepo with two distinct codebases:
- **Backend (Python/FastAPI)** — `server/` directory
- **Frontend (React/JavaScript)** — `hoopprophet/` directory

The backend is the primary focus, with a well-structured data pipeline and ML system. The frontend is a single-file React SPA.

## Naming Patterns

**Python Files:**
- Use `snake_case`: `nba_client.py`, `feature_config.py`, `dnp_synthesis.py`
- Test files: `test_` prefix with `snake_case`: `test_nba_client.py`, `test_feature_pipeline.py`
- Module packages use `__init__.py` with lowercase names: `pipeline/`, `collectors/`, `processors/`

**Python Functions & Variables:**
- Functions: `snake_case` — e.g., `compute_rolling_features()`, `synthesize_dnp_rows()`
- Private helpers: `_` prefix — e.g., `_extract_opponent()`, `_make_client()`, `_seed_player()`
- Constants: `UPPER_SNAKE_CASE` — e.g., `PRIMARY_STATS`, `WINDOWS_PRIMARY`, `CACHE_PATH`
- DataFrame variables: `_df` suffix — e.g., `game_logs_df`, `team_stats_df`, `played_df`

**Python Classes:**
- `PascalCase` — e.g., `NBAClient`
- Test classes: `PascalCase` with `Test` prefix — e.g., `TestGameLogsStored`, `TestDNPSynthesis`

**React/JavaScript Files:**
- `PascalCase` for components: `App.js`
- Entry point: `index.js`

## Code Style

**Python Formatting:**
- 4-space indentation
- Line length: not strictly enforced, but generally kept under 100-120 characters
- String quotes: single quotes in `server/pipeline/`, mixed in `server/ml/` and `server/app.py`
- No formatter/linter config files detected (no `.eslintrc` beyond CRA default, no `black`, `ruff`, or `isort` config)

**JavaScript Formatting:**
ESLint configured via `react-app` and `react-app/jest` presets in `package.json` `eslintConfig`
- 2-space indentation (CRA default)
- Single and double quotes mixed

**Python Imports:**
Order in `server/pipeline/` modules:
1. Standard library: `import logging`, `import os`, `import time`
2. Third-party: `import pandas as pd`, `from tenacity import ...`
3. Local: `from server.pipeline.feature_config import ...`, `from server.pipeline.db.queries import ...`

Implicit relative imports used within `server/ml/`:
```python
from .dataset import build_dataset
from .prop_line import get_prop_line
```

Absolute imports used from `server/` package:
```python
from server.pipeline import SEASONS, DATA_DIR, DB_PATH, CACHE_PATH
from server.pipeline.nba_client import NBAClient
```

## Error Handling

**Backend (Python):**

FastAPI endpoints use generic `try/except Exception` with `HTTPException`:
```python
try:
    # business logic
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error fetching ...: {str(e)}")
```

Pipeline modules use `logging.getLogger(__name__)` and propagate exceptions upward:
```python
# Collectors catch, log, mark progress as "failed", and continue
except Exception as e:
    logger.error("Failed for player %d season %s: %s", player_id, season, e)
    queries.mark_progress(conn, "player_gamelog", player_id, season, "failed", str(e))
```

Retry logic uses `tenacity` decorator on `NBAClient` methods:
```python
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=0.6, max=30, jitter=2),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
```

Empty API responses raise `ValueError` to trigger tenacity retry:
```python
if df.empty:
    raise ValueError(f"Empty gamelog for player {player_id} season {season}")
```

**Frontend (JavaScript):**

Async operations use `try/catch` with `console.error` and user-facing status messages:
```javascript
try {
    const response = await fetch(`${API_BASE}/predict`, { ... });
    if (!response.ok) throw new Error('Prediction failed');
    // process response
} catch (error) {
    console.error('Error making prediction:', error);
    setPredictionStatus('Prediction failed. Please try again.');
}
```

## Logging

**Backend:** Python `logging` module with named loggers:
```python
logger = logging.getLogger(__name__)
logger.info("Fetched %d games for player %d season %s", len(df), player_id, season)
logger.error("Failed for player %d season %s: %s", player_id, season, e)
```

Ingest CLI configures logging format:
```python
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.DEBUG if args.verbose else logging.INFO,
)
```

**Frontend:** `console.log()` and `console.error()` — debug statements left in production code (e.g., `console.log('Players data:', playersData?.slice(0, 5))`).

## Comments

**Backend (Python):**
- Module-level docstrings on pipeline functions: `"""Compute rolling and season-to-date features with a temporal guard."""`
- Inline comments explain business logic decisions
- `__init__.py` modules in `server/pipeline/` subpackages are empty (no docstrings needed)

**Frontend (JavaScript):**
- JSX section comments: `{/* Navigation */}`, `{/* Player Selection */}`
- Some debug comments left in code

## Function Design

**Size:** Pipeline functions are well-scoped and focused (20-100 lines). The `app.py` endpoints vary — `/predict` is ~60 lines with inline step-by-step logging.

**Parameters:** Python type hints used in `server/pipeline/`:
```python
def compute_rolling_features(played_df: pd.DataFrame) -> pd.DataFrame:
def synthesize_dnp_rows(conn: sqlite3.Connection, season: str) -> int:
def run_feature_pipeline(conn, output_path: str | None = None) -> dict:
```

Type hints are absent from `server/ml/` and `server/app.py`.

**Return Values:**
- Collectors return `dict` with stats: `{"completed": N, "failed": N, "skipped": N}`
- Pipeline functions return `pd.DataFrame` or summary `dict`
- `NBAClient` methods return `pd.DataFrame` or `list[dict]`

## Module Design

**Exports:** Each module exports functions directly — no barrel files except `__init__.py` for package path constants.

**Package structure:**
- `server/pipeline/__init__.py` — exports constants (`SEASONS`, `DATA_DIR`, `DB_PATH`, `CACHE_PATH`)
- `server/pipeline/db/__init__.py` — re-exports from `queries` module
- `server/pipeline/collectors/__init__.py` — empty
- `server/pipeline/processors/__init__.py` — empty

## Data Conventions

**Feature Naming:**
- Rolling averages: `{stat}_avg_L{window}` — e.g., `pts_avg_L5`, `reb_avg_L10`
- Rolling std deviations: `{stat}_std_L{window}` — e.g., `pts_std_L5`
- Season averages: `{stat}_season_avg`
- Combo stats: `pra_avg_L5` (points + rebounds + assists), `pa_avg_L10`, `pr_avg_L20`
- Contextual features: `rest_days`, `is_b2b`, `is_home`, `opp_def_rating`, `opp_pace`, `team_pace`, `position`
- Matchup features: `matchup_avg_{stat}`

**Database:**
- SQLite with WAL mode and foreign keys
- Table columns use `snake_case`
- `INSERT OR IGNORE` for idempotent inserts (game logs, schedules, rosters)
- `INSERT OR REPLACE` for upserts (players, teams, team stats)
- Progress tracking: `collection_progress` table with `status` field (`pending`, `completed`, `failed`)

**API Response Format:**
- Pydantic models define request/response schemas: `PredictionRequest`, `PredictionResponse`, `PropLineResponse`
- Snake_case field names in API: `player_name`, `opponent_team_abv`

## Configuration Patterns

**Environment Variables:**
- Frontend: `REACT_APP_API_BASE` (falls back to `http://localhost:8000`)
- Backend: `GEMINI_API_KEY` (for LLM summary generation)

**Config Files:**
- Pipeline constants in `server/pipeline/feature_config.py`: `ALL_TARGET_STATS`, `PRIMARY_STATS`, `WINDOWS_PRIMARY`, `MIN_GAMES_PER_SEASON`, `N_THRESHOLD_LINES`
- Seasons list in `server/pipeline/__init__.py`: `SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]`

---

*Convention analysis: 2026-04-17*