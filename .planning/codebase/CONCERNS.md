# Codebase Concerns

**Analysis Date:** 2025-03-22

## Tech Debt

**Monolithic frontend (`hoopprophet/src/App.js`):**
- Issue: Single component holds theme, data fetching, layout, forms, and prediction UI (~591 lines) with no route-based or component-based lazy loading.
- Files: `hoopprophet/src/App.js`
- Impact: Harder to test, review, and extend; every change risks regressions across the whole screen.
- Fix approach: Split into `components/`, `hooks/` (e.g. `usePlayers`, `usePrediction`), and optional `routes/` if the app grows; use `React.lazy` for heavy sections if code-splitting is added.

**ML path runs full cross-validation on every prediction request:**
- Issue: `POST /predict` calls `build_dataset()` → `train_models()` → `predict_stats()`. `train_models()` uses `RepeatedKFold(n_splits=10, n_repeats=10)` (`server/ml/model_train.py`) and evaluates Linear Regression and XGBoost per stat for eight stats—very expensive per HTTP request. `predict_stats()` then fits pipelines again per stat (`pipeline_lr.fit` / `pipeline_xgb.fit` in `server/ml/model_train.py`), duplicating work after CV already selected a model.
- Files: `server/app.py`, `server/ml/model_train.py`, `server/ml/dataset.py`
- Impact: High latency, CPU load, and poor scalability under concurrent users.
- Fix approach: Cache trained artifacts per `(player_id, opponent, season window)`; precompute or batch training offline; reduce CV folds for online path; fit a single final model per stat once after model selection.

**Duplicate `get_player_id` implementations:**
- Issue: Nearly identical player lookup exists in `server/ml/dataset.py` and `server/ml/prop_line.py` (and `get_player_id` from `ml.prop_line` is imported in `server/app.py` while `dataset.build_dataset` uses the local one in `dataset.py`).
- Files: `server/ml/dataset.py`, `server/ml/prop_line.py`, `server/app.py`
- Impact: Behavior can diverge; bugs fixed in one copy may not propagate.
- Fix approach: Single shared module (e.g. `server/ml/players.py`) with one `get_player_id` and consistent error handling.

**Print-based logging:**
- Issue: `print()` is used for step tracing and errors across the stack instead of structured logging with levels.
- Files: `server/app.py` (lines ~190–251), `server/ml/model_train.py`, `server/ml/dataset.py`, `server/ml/prop_line.py`
- Impact: No log levels, harder filtering in production, and traceback printing on every prediction failure may clutter or leak detail to log aggregators.
- Fix approach: Use `logging` with a named logger; gate debug steps behind `DEBUG`; avoid printing full tracebacks in production or route them to error tracking only.

**Unpinned Python dependencies:**
- Issue: `server/requirements.txt` lists packages without version pins.
- Files: `server/requirements.txt`
- Impact: Reproducible builds and security audits are harder; CI and prod can drift silently.
- Fix approach: Pin with `pip freeze` or a lock workflow (e.g. `pip-tools`) and revisit periodically.

## Known Bugs

**Player name mismatch raises `IndexError` (uncaught as HTTP 500):**
- Symptoms: Requesting a player name not present in the active roster can crash inside `get_player_id` when indexing `.values[0]` on an empty selection.
- Files: `server/ml/dataset.py` (e.g. lookup around line 23), `server/ml/prop_line.py` (e.g. line 13)
- Trigger: `/predict` or dataset build with a typo or inactive player name not in the filtered frame.
- Workaround: Use exact names from `/players` only; no API-level validation before lookup.

**Docstring / model name drift for Gemini:**
- Symptoms: Comment in `generate_model_summary` references “Gemini 2.5 Flash” while code uses `genai.GenerativeModel('gemini-2.0-flash-exp')`.
- Files: `server/ml/model_train.py` (lines ~156–173)
- Trigger: N/A for runtime; confuses maintainers and may break if the experimental model ID is retired.
- Workaround: None required for users; update model ID and comment together when rotating models.

## Security Considerations

**Exception strings returned to API clients:**
- Risk: `HTTPException(detail=f"... {str(e)}")` exposes internal error messages from dependencies to callers.
- Files: `server/app.py` (multiple handlers, e.g. lines 83–84, 101–102, 180–181, 247–252)
- Current mitigation: None beyond FastAPI’s JSON error body.
- Recommendations: Return generic messages in production; log full exceptions server-side only.

**Full traceback printed on prediction failure:**
- Risk: Stack traces in stdout may include paths, library versions, or data snippets depending on the exception.
- Files: `server/app.py` (lines ~247–251)
- Current mitigation: None.
- Recommendations: Log via `logging.exception` behind appropriate level; disable verbose traceback in production unless integrated with a secure log sink.

**`GEMINI_API_KEY` via environment:**
- Risk: Keys in plain host environment or shell history; Compose passes `GEMINI_API_KEY=${GEMINI_API_KEY}` from the host.
- Files: `docker-compose.yml` (lines 9–10), `server/ml/model_train.py` (lines 168–172)
- Current mitigation: Key is not hardcoded; missing key yields a safe string response for the summary only.
- Recommendations: Use a secrets manager or Docker secrets in production; never commit `.env`; restrict who can read deployment env.

**CORS allowlist:**
- Risk: Only `http://localhost:3000` and `http://frontend:3000` are allowed (`server/app.py` lines 16–25). Production domains must be added deliberately; `allow_credentials=True` requires exact origin matching.
- Files: `server/app.py`
- Current mitigation: Narrow origins for dev/Docker.
- Recommendations: Drive allowed origins from configuration per environment; avoid `*` with credentials.

## Performance Bottlenecks

**NBA `player_inactive` loop with `time.sleep(1)`:**
- Problem: One second delay per team game ID when calling box score summaries serially.
- Files: `server/ml/dataset.py` (lines 75–85)
- Cause: Rate-limit avoidance for the unofficial NBA stats API.
- Improvement path: Batch or cache box score queries; reduce calls if inactivity can be inferred elsewhere; backoff/retry library instead of fixed sleep.

**Repeated static NBA data fetches:**
- Problem: `get_players()` / `get_teams()` are invoked inside handlers (`server/app.py` `/players`, `/teams`, `/player/...`) and during player resolution without application-level caching.
- Files: `server/app.py`, `server/ml/dataset.py`, `server/ml/prop_line.py`
- Cause: Direct `nba_api` usage each time.
- Improvement path: In-memory cache with TTL for static lists; warm cache at startup.

**Prediction endpoint computational cost:**
- Problem: See Tech Debt—full CV plus per-stat refits per request dominates latency.
- Files: `server/ml/model_train.py`, `server/app.py`
- Cause: Design treats each request as a fresh training job.
- Improvement path: Async job queue for heavy runs; or precomputed models as above.

## Fragile Areas

**`dataset_cleaning` merge path when `team_games` is empty:**
- Files: `server/ml/dataset.py` (lines 121–126)
- Why fragile: Warning branch skips merge; downstream assumptions about columns and row alignment may differ from the common path.
- Safe modification: Add tests for empty `team_games` and verify `gamelog` schema matches expectations.
- Test coverage: No automated tests in repo (see below).

**External NBA and Gemini APIs:**
- Files: `server/ml/dataset.py`, `server/ml/prop_line.py`, `server/ml/model_train.py`
- Why fragile: Undocumented rate limits, API shape changes, or deprecated Gemini model IDs can break runtime behavior.
- Safe modification: Centralize HTTP/API calls; timeouts and retries; feature flags for model ID.

## Scaling Limits

**`/predict` synchronous design:**
- Current capacity: Single-threaded request handling per worker; each prediction does heavy CPU and many I/O calls to NBA endpoints.
- Limit: Few concurrent predictions before timeouts or NBA throttling.
- Scaling path: Horizontal scaling with queue workers; separate read-only API tier for static lists; caching.

## Dependencies at Risk

**`google-generativeai` and experimental model ID:**
- Risk: `gemini-2.0-flash-exp` may change availability or behavior without notice.
- Impact: `generate_model_summary` fails or returns error strings embedded in the UI response path.
- Migration plan: Pin SDK version; switch to a stable model name; handle API errors without failing the whole `/predict` response (optional partial failure).

**Unpinned `nba_api` and stack:**
- Risk: Upstream changes to endpoints or response schemas.
- Impact: Pandas operations assume specific columns (e.g. `Game_ID`, `PLAYER_ID`).
- Migration plan: Pin versions; add integration tests against recorded fixtures.

## Missing Critical Features

**Automated tests:**
- Problem: No `*.test.*` / `*.spec.*` files found; `hoopprophet/package.json` exposes `npm test` (CRA) but there are no test files exercising React or API contracts.
- Blocks: Safe refactoring of `App.js` and ML modules; regression detection for API and dataset edge cases.

**Observability:**
- Problem: No structured metrics or error tracking integration detected in application code.
- Blocks: Production debugging and SLO definition.

## Test Coverage Gaps

**Entire application surface:**
- What's not tested: FastAPI routes, ML training/predict paths, `build_dataset`, and React UI.
- Files: `server/app.py`, `server/ml/*`, `hoopprophet/src/App.js`
- Risk: Regressions in player lookup, NBA failures, and UI flows go unnoticed.
- Priority: High for ML and API; Medium for pure UI until components are split.

---

*Concerns audit: 2025-03-22*
