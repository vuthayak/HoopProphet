# Codebase Concerns

**Analysis Date:** 2026-04-17

## Tech Debt

### Dual Prediction Systems — Old `ml/` vs. New `pipeline/`

- Issue: Two completely separate prediction paths exist. The live `/predict` API endpoint uses the old `server/ml/` modules (`dataset.py`, `model_train.py`, `prop_line.py`) that train models from scratch per request. The newer `server/pipeline/` system has proper feature engineering (rolling features, contextual features, matchup features, DNP synthesis, target generation) but is **not wired into the API at all**.
- Files: `server/app.py` lines 8-10, `server/ml/dataset.py`, `server/ml/model_train.py`, `server/ml/prop_line.py` vs. `server/pipeline/features.py` + `server/pipeline/processors/`
- Impact: The API serves predictions from a simplistic, data-leaky model. The well-engineered pipeline (with temporal guards, DNP handling, proper feature engineering) produces only a static Parquet file unused by any endpoint. Any improvements to the pipeline have zero effect on user-facing predictions.
- Fix approach: Connect `/predict` (or a new endpoint) to the pipeline's feature store and trained models. The pipeline should persist trained models and the API should load cached models rather than training fresh per request. Start by exposing `run_feature_pipeline` output via an endpoint, then add model serving.

### Model Training on Every Request

- Issue: `server/app.py` line 210 calls `train_models(data)` on every `/predict` request, which performs 10×10 repeated K-fold cross-validation for 8 stats (800 total model fits per request). With `XGBRegressor(n_estimators=200)`, this can take 30+ seconds per prediction.
- Files: `server/ml/model_train.py` (lines 49-99 for `train_models`, lines 101-127 for `predict_stats`), `server/app.py` (line 210)
- Impact: Extremely slow API response times. Makes the app unusable for real-time use. Wastes compute. No model persistence means identical training for the same player across requests.
- Fix approach: Train models asynchronously (e.g., nightly via the pipeline CLI), persist them to disk (`joblib` or `pickle`), and load cached models in the API endpoint. Return cached predictions or retrain only when data changes.

### Duplicate `get_player_id` Function

- Issue: The same function `get_player_id(player_name)` is implemented identically in both `server/ml/dataset.py` (line 16) and `server/ml/prop_line.py` (line 6). Additionally, `server/app.py` reimplements the same logic inline when it calls the NBA API's `get_players()` directly in the `/players` and `/player/{player_name}` endpoints.
- Files: `server/ml/dataset.py` line 16, `server/ml/prop_line.py` line 6, `server/app.py` lines 72-81 and 138-147
- Impact: Divergent behavior risk if one copy is updated but not the other. Three separate calls to `nba_api.stats.static.players.get_players()` can occur during a single `/predict` request.
- Fix approach: Consolidate to a single shared utility (e.g., `server/pipeline/nba_client.py` already has `get_all_active_players`). Remove duplicates from `ml/dataset.py` and `ml/prop_line.py`.

### Data Leakage in Old ML Pipeline

- Issue: `server/ml/dataset.py`'s `dataset_cleaning()` function (line 120) merges player gamelogs with team games via right join and concatenates rivalry games, but does **not** shift rolling features. The dataset used for training includes the current game's stats in the prediction features. By contrast, `server/pipeline/processors/rolling_features.py` (line 71-72) correctly applies `.shift(1)` to prevent temporal leakage.
- Files: `server/ml/dataset.py` line 120, `server/pipeline/processors/rolling_features.py` lines 71-72
- Impact: Predictions from `ml/model_train.py` are inherently data-leaky — the model sees current-game stats when predicting current-game outcomes. This inflates R² during cross-validation but degrades real predictive accuracy.
- Fix approach: Replace `ml/` prediction path with the pipeline-based approach that uses proper temporal guards. At minimum, add a shift in the old `dataset_cleaning` if it must remain.

### Single-File Frontend Architecture

- Issue: The entire React frontend (all state, API calls, UI rendering, theming) lives in one 591-line `App.js` file with no component extraction.
- Files: `hoopprophet/src/App.js`
- Impact: Difficult to maintain, test, or reuse. Any change risks regressions in unrelated parts of the UI. No separation of concerns between data fetching, state management, and presentation.
- Fix approach: Decompose into components: `PlayerSelect`, `TeamSelect`, `PredictionsDisplay`, `PredictionCard`, `PropLineAnalysis`, `ModelSummary`. Extract a custom hook for API calls (`usePlayers`, `useTeams`, `usePrediction`). Move theme to a separate file.

### Hardcoded Stat List in Old ML Module

- Issue: The prediction stat list `['PTS', 'REB', 'AST', 'FG3M', 'STL', 'BLK', 'TRIPLE_DOUBLE', 'DOUBLE_DOUBLE']` is hardcoded in three places within `model_train.py` (lines 56, 115) and `dataset.py` line 132. The pipeline uses a different, more comprehensive stat list (`feature_config.py`: `STAT_COLS`, `PRIMARY_STATS`, `ALL_TARGET_STATS`) that includes `FGM`, `FGA`, `FTM`, `FTA`, etc. and uses lowercase naming.
- Files: `server/ml/model_train.py` lines 56/115, `server/ml/dataset.py` line 132, `server/pipeline/feature_config.py`
- Impact: The old ML path operates on a subset of features with inconsistent naming (uppercase vs lowercase). Makes it impossible to align the two systems.
- Fix approach: Consolidate stat definitions into `feature_config.py` as the single source of truth. Migrate old ML code to reference this config.

## Known Bugs

### `dataset.py` Right-Join Loses Player-Only Games

- Issue: `dataset_cleaning()` uses `pd.merge(player_gamelog, team_games, how='right', on=['Game_ID','MATCHUP', 'WL'])` (line 123). The right join means if a player has game logs that don't match any team game (different matchup format, data inconsistency), those rows are silently dropped. The comment says "right" but semantically a left join preserving player games would be more correct.
- Files: `server/ml/dataset.py` line 123
- Impact: Some player game logs may be silently dropped from the training dataset, potentially missing key games.
- Workaround: None currently. The pipeline's proper approach avoids this entirely.

### `team_games` Variable Unbound on Empty Path

- Issue: In `dataset.py` `get_team_games()`, if the current season has <=20 games AND the previous season's data leads to an exception, the `team_gamelog` variable may not be assigned before the function tries to return it at line 61 (since the if/else branches assign to different variable names `team_gamelog` vs. `curr_team_gamelog`). Actually looking closer, `team_gamelog` is assigned in both branches, but `used_prev_season` could be `False` while `team_gamelog` references the wrong variable. More critically, if the NBA API call on line 49 throws an exception, neither `curr_team_gamelog` nor `team_gamelog` is assigned.
- Files: `server/ml/dataset.py` lines 48-61
- Impact: Unhandled `UnboundLocalError` if the NBA API call fails for a team in the current season.
- Workaround: The pipeline system handles this with proper retry logic in `NBAClient`.

### Prop Line Returns Single Row — IndexError Risk

- Issue: `server/ml/prop_line.py` `get_prop_line()` accesses `prop_line.iloc[0]` at the caller site in `app.py` line 173 (`prop_lines_dict = prop_line.iloc[0].to_dict()`). If `playercareerstats` returns an empty DataFrame (e.g., for a player with no career stats), this raises an `IndexError` with a stack trace exposed to the user.
- Files: `server/app.py` line 173, `server/ml/prop_line.py` line 34
- Impact: 500 error for players with no career stats data.
- Workaround: The generic `try/except` in the `/predict` endpoint catches this, but returns a raw error string to the user.

## Security Considerations

### No Authentication or Rate Limiting

- Risk: The FastAPI backend has no authentication, authorization, or rate limiting on any endpoint. The `/predict` endpoint triggers expensive operations (multiple NBA API calls + full model training + external Gemini API call), making it trivially exploitable for compute and API cost abuse.
- Files: `server/app.py` (all endpoints)
- Current mitigation: None
- Recommendations: Add API key authentication middleware. Implement rate limiting (e.g., `slowapi`). Consider request throttling specifically for `/predict`. Move model training to background jobs.

### Overly Permissive CORS

- Risk: The CORS middleware in `server/app.py` (lines 16-25) allows `allow_methods=["*"]` and `allow_headers=["*"]` from the specified origins. While origins are limited to `localhost:3000` and `frontend:3000`, the wildcard methods/headers means any HTTP method (including DELETE, PUT) is allowed.
- Files: `server/app.py` lines 16-25
- Current mitigation: Origin restrictions are in place
- Recommendations: Restrict `allow_methods` to `["GET", "POST"]` only. Remove `allow_credentials=True` unless needed (it's currently set but no auth mechanism uses cookies).

### Error Details Leaked to Clients

- Risk: The `/predict` endpoint's error handler (line 252) returns `f"Error making prediction: {str(e)}"` directly in the HTTP response. This can expose internal implementation details, NBA API error messages, and database schema information to clients. The handler also imports `traceback` inline (line 250) and prints full traceback to server logs.
- Files: `server/app.py` lines 247-252
- Current mitigation: None
- Recommendations: Return generic error messages to clients (e.g., "Prediction failed. Please try again."). Log detailed errors server-side only. Remove the inline `import traceback`.

### Gemini API Key Without Validation

- Risk: The `GEMINI_API_KEY` environment variable is checked only inside `generate_model_summary()` (line 169). If the key is missing, the function returns a string "Model summary unavailable: GEMINI_API_KEY not set" which is surfaced directly in the API response. If the key is invalid/expired, the raw error string from Google's API is returned to the client.
- Files: `server/ml/model_train.py` lines 168-202
- Current mitigation: Basic `if not api_key` check
- Recommendations: Validate the API key at application startup. Return a generic error message to clients when the summary fails. Never leak `str(e)` from external API calls.

### Debug Print Statements in Production

- Risk: `server/app.py` and `server/ml/` modules contain 25+ `print()` statements with emoji-prefixed debug logging (e.g., `"🏀 Starting prediction..."`, `"📍 Step 1..."`). These produce verbose, unstructured logs in production. The `/predict` endpoint prints the entire prediction results dict and dataset shapes, which could leak sensitive data to logs.
- Files: `server/app.py` lines 190-236, `server/ml/dataset.py` (multiple), `server/ml/model_train.py` (lines 46, 54, 113, 138), `server/ml/prop_line.py` (line 14)
- Impact: Noisy logs, potential data leakage, unstructured log format prevents proper monitoring/alerting
- Recommendations: Replace all `print()` statements with Python `logging` module calls. Use appropriate log levels (DEBUG for step-by-step, INFO for summaries). Log structured data, not raw dicts.

## Performance Bottlenecks

### Blocking Model Training on Every Prediction

- Problem: Each `/predict` request triggers `build_dataset()` (5+ synchronous NBA API calls with rate-limit delays), `train_models()` (800 model fits via 10×10 RepeatedKFold), and `generate_model_summary()` (an external Gemini API call). Total latency can exceed 60 seconds.
- Files: `server/app.py` lines 188-245, `server/ml/model_train.py` lines 49-99
- Cause: No caching, no background processing, no model persistence
- Improvement path: (1) Cache trained models per player/team pair. (2) Pre-train models nightly. (3) Use async endpoints with background tasks. (4) Cache NBA API responses (the pipeline's `NBAClient` already has HTTP caching but the old `ml/` path doesn't use it).

### NBA API Calls Without Caching in Old ML Path

- Problem: The `server/ml/dataset.py` module makes 5-8 sequential NBA API calls per prediction request (`get_players`, `CommonPlayerInfo`, `PlayerGameLog` ×2, `TeamGameLog` ×2, `BoxScoreSummaryV2` per game for inactive check). None of these use the `requests_cache.CachedSession` configured in the pipeline's `NBAClient`. Each call has a `time.sleep(1)` for the inactive player check.
- Files: `server/ml/dataset.py` lines 16-98
- Cause: The old ML module predates the pipeline and doesn't use the `NBAClient` abstraction
- Improvement path: Refactor `dataset.py` to use `NBAClient` for all API calls. This would get automatic caching and retry behavior. Alternatively, replace the entire `ml/` path with the pipeline.

### Synchronous External API Call for Every Prediction

- Problem: `generate_model_summary()` in `model_train.py` calls the Gemini API synchronously for every prediction request. This adds network latency (1-5 seconds) and can fail if Google's API is slow or rate-limited.
- Files: `server/ml/model_train.py` lines 156-202
- Cause: No caching of summaries, synchronous call
- Improvement path: Cache summary responses. Use the Gemini API asynchronously with FastAPI's async support. Consider generating summaries as a background task.

### Frontend Re-fetches Players and Teams on Every Mount

- Problem: `App.js` `useEffect` (lines 60-84) fetches `/players` and `/teams` on every component mount. Each call hits the NBA API directly (no caching on the backend). These lists change rarely (only during offseason).
- Files: `hoopprophet/src/App.js` lines 60-84, `server/app.py` lines 65-84 and 86-102
- Cause: No caching on backend, no stale-while-revalidate pattern on frontend
- Improvement path: Cache player/team lists in the backend with a TTL (e.g., 1 hour). Use React Query or SWR on the frontend for caching and background refresh.

## Fragile Areas

### NBA API Column Name Dependencies

- Files: `server/ml/dataset.py`, `server/pipeline/collectors/game_logs.py` (lines 13-35, `GAMELOG_COLUMN_MAP`)
- Why fragile: The NBA API returns DataFrames with specific column names (e.g., `Player_ID`, `Game_ID`, `FG3M`). If nba_api changes any column name in a version update, the entire pipeline and old ML module break. The pipeline has a `GAMELOG_COLUMN_MAP` that provides some insulation, but the old `dataset.py` uses column names directly without a mapping layer.
- Safe modification: Always use the `GAMELOG_COLUMN_MAP`-style pattern for nba_api column access. Pin `nba_api==1.11.4` in `requirements.txt` (already done). Add integration tests that validate column names against the actual API response.
- Test coverage: No tests for old `dataset.py` at all. Pipeline has tests for game log collection.

### Season Configuration Hardcoding

- Files: `server/pipeline/__init__.py` line 3, `server/ml/dataset.py` lines 29-41
- Why fragile: `SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]` is hardcoded. When the 2025-26 season starts, someone must manually update this list. The `get_season()` function in `dataset.py` dynamically computes the current season, but the pipeline requires explicit configuration.
- Safe modification: Compute `SEASONS` dynamically starting from a configurable lookback years parameter. Add a config file or environment variable for season range.
- Test coverage: `test_ingest.py` tests the pipeline mock but doesn't verify season boundaries

### Matchup Feature Abbreviation Mapping

- Files: `server/pipeline/processors/contextual_features.py` lines 37-39, `server/pipeline/processors/matchup_features.py` lines 31-37
- Why fragile: Opponent team identification relies on parsing the `matchup` field (e.g., `"DEN vs. LAL"` or `"DEN @ PHX"`) and mapping the extracted abbreviation to a team ID. This mapping comes from the `teams` database table. Any team with an abbreviation that appears differently in the matchup string (e.g., historical abbreviation changes) would silently produce `NaN` for opponent features.
- Safe modification: Add validation/logging for unmatched abbreviations. Consider a fallback mapping for known alternate abbreviations.
- Test coverage: `test_contextual_features.py` tests `is_home` parsing but not abbreviation edge cases

### XGBoost Configuration Not Tuned

- Files: `server/ml/model_train.py` line 32
- Why fragile: `XGBRegressor(n_estimators=200, learning_rate=0.01, max_depth=3, random_state=101)` has a very slow learning rate (0.01) with moderate tree count (200). This configuration hasn't been tuned via hyperparameter search. The low learning rate combined with only 200 estimators may produce underfitting.
- Safe modification: Run hyperparameter optimization (GridSearchCV or Optuna). Consider faster default params for the real-time use case (higher learning rate, fewer estimators).
- Test coverage: No model performance tests exist at all

## Scaling Limits

### Concurrent Prediction Requests

- Current capacity: 1 concurrent prediction (model training blocks the single uvicorn worker)
- Limit: If 2 users request predictions simultaneously, both will train models from scratch, potentially hitting NBA API rate limits and doubling latency
- Scaling path: (1) Pre-train and cache models. (2) Add multiple uvicorn workers. (3) Use async endpoints with background task queues (Celery/Redis). (4) Implement request deduplication for identical player/team combos.

### NBA API Rate Limits

- Current capacity: The old `ml/` path has no rate limiting; the new pipeline has a 0.6s minimum delay between calls
- Limit: The NBA stats API has undocumented rate limits (~60 requests/minute). The old prediction path makes 5-8 calls per request, so ~8-10 requests/minute would hit limits. The inactive player check (`player_inactive`) makes 1 API call + `time.sleep(1)` per game.
- Scaling path: Use the pipeline's `NBAClient` with caching for all API access. Pre-fetch and cache data. Move batch operations to the pipeline CLI.

### SQLite Database Under Concurrent Writes

- Current capacity: SQLite with WAL mode (configured in `server/pipeline/db/connection.py`)
- Limit: SQLite works for single-writer scenarios. Multiple uvicorn workers writing simultaneously to `hoopprophet.db` would encounter lock contention.
- Scaling path: For the pipeline (batch writes), SQLite is fine. For the API serving path, switch to PostgreSQL or use SQLite in read-only mode with periodic batch updates.

## Dependencies at Risk

### `react-scripts` 5.0.1 (CRA Deprecation)

- Risk: `react-scripts` (Create React App) has been effectively deprecated. The package hasn't had a meaningful update in years. `react-scripts@5.0.1` uses Webpack 4, which doesn't support modern JavaScript features efficiently.
- Impact: Build performance issues, security vulnerabilities in transitive dependencies, no future updates
- Migration plan: Migrate to Vite (`vite-plugin-react`). It's the modern standard and provides faster builds/refresh.

### Pinned `nba_api==1.11.4`

- Risk: `requirements.txt` pins `nba_api==1.11.4` exactly. This is good for stability but means the project won't receive bug fixes or new features from the NBA API library without manual updating.
- Impact: If the NBA changes their API, the pinned version may silently return stale/incorrect data
- Migration plan: Pin to a compatibility range (e.g., `nba_api>=1.11,<2`) and add integration tests.

### No Version Pinning for Many Dependencies

- Risk: `requirements.txt` has many unpinned or loosely pinned dependencies: `fastapi`, `uvicorn`, `scikit-learn`, `xgboost`, `pandas>=2.2.0`, `numpy>=2.1.0`, `pyarrow>=19.0.0`. These could break with major version updates.
- Files: `server/requirements.txt`
- Impact: `pip install -r requirements.txt` in a fresh environment may install an incompatible version
- Migration plan: Pin all dependencies to exact versions or minimum compatible ranges. Use `pip freeze > requirements.lock` for reproducible builds.

## Missing Critical Features

### No Frontend Error Boundaries

- Problem: The React frontend has no error boundaries. If any render throws, the entire app crashes with a white screen.
- Files: `hoopprophet/src/App.js`
- Blocks: Graceful error recovery; showing meaningful error messages to users

### No Loading States for Endpoints Other Than `/predict`

- Problem: The `/players` and `/teams` endpoints have no server-side caching. Each call triggers a full NBA API query. The frontend shows a loading state but the backend can be slow.
- Files: `server/app.py` lines 65-102
- Blocks: Fast page load; reliable dropdown population

### No Prediction Caching

- Problem: Identical prediction requests (same player/team) trigger a full model retraining. There's no caching layer for predictions.
- Files: `server/app.py` lines 183-252
- Blocks: Responsive repeated predictions; reasonable API cost

### No Background Task System

- Problem: All expensive operations (data collection, model training) run synchronously in the request handler. There's no task queue or background worker system.
- Files: `server/app.py`
- Blocks: Non-blocking predictions; scheduled model retraining

## Test Coverage Gaps

### Old ML Module (`ml/`) — Zero Test Coverage

- What's not tested: `server/ml/dataset.py`, `server/ml/model_train.py`, `server/ml/prop_line.py` have **no tests at all**. These modules are what the live API uses for predictions.
- Files: `server/ml/dataset.py`, `server/ml/model_train.py`, `server/ml/prop_line.py`
- Risk: Data leakage bugs, wrong predictions, NBA API changes, model configuration errors could all go undetected
- Priority: **High** — This is the core prediction logic serving users

### FastAPI Endpoints — Zero Test Coverage

- What's not tested: None of the `server/app.py` endpoints (`/players`, `/teams`, `/team/{name}`, `/player/{name}`, `/predict`, `/prop-line`, `/health`) have API tests.
- Files: `server/app.py`
- Risk: Endpoint regressions, CORS issues, error handling changes, request validation problems
- Priority: **High** — These are the user-facing API surface

### Frontend — Zero Test Coverage

- What's not tested: `hoopprophet/src/App.js` has no component tests, no integration tests, no E2E tests.
- Files: `hoopprophet/src/App.js`
- Risk: UI regressions, broken API integration, state management bugs
- Priority: **Medium** — UI bugs are visible but not data-critical

### Pipeline Model Integration — Disconnected

- What's not tested: The connection between the pipeline's feature engineering output and any model training. The pipeline produces a Parquet file, but no code trains a model from it or serves predictions from it.
- Files: `server/pipeline/features.py` output → no consumer
- Risk: Feature engineering improvements don't reach users; pipeline could produce malformed data undetected
- Priority: **High** — The pipeline is a major investment that's currently unused

### Gemini API Summary — No Test Coverage

- What's not tested: `server/ml/model_train.py` `generate_model_summary()` calls the external Gemini API with no mocking, no error handling tests, and no timeout configuration.
- Files: `server/ml/model_train.py` lines 156-202
- Risk: API failures leak error strings to users; no timeout means hung requests; hallucinated summaries could contain harmful content
- Priority: **Medium** — External API dependency with no safety net

---

*Concerns audit: 2026-04-17*