# Phase 5: API Layer & Prop Serving - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend API serving prop predictions, hit rates, and player data from cached artifacts — replacing V1's per-request model training and live NBA API calls. The API loads the trained LightGBM model artifact at startup, serves predictions from pre-computed features (not on-the-fly), and exposes player/team/game-log/prop/hit-rate endpoints from SQLite cache. Frontend integration is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Default Line Derivation
- **D-01:** Use **median** of last 20 non-DNP games for default stat lines, rounded to 0.5 increments (sportsbook-style). Median is robust to outliers — a 50-point game doesn't skew the line.
- **D-02:** Minimum 5 games required to compute a default line. If a player has fewer than 5 games, that stat is excluded from default lines.
- **D-03:** Combo stats (PRA, PA, PR) computed from median of component stat sums, not median of computed combo values.

### Top Prop Ranking
- **D-04:** Filter stats by volume and relevance: exclude stats where a player averages <1.0 per game (low-volume, irrelevant props — e.g., a guard's blocks). Select top 5 stats by volume x variance.
- **D-05:** Rank top props by **model-predicted probability** (descending). Show hit rates alongside each prop for validation — probability determines order, hit rates provide context.
- **D-06:** Maximum 5 props per player (per PROP-04).

### API Response Shape
- **D-07:** Lean JSON responses — only essential fields. No redundant metadata. Frontend can fetch player context separately via the player endpoint.
- **D-08:** Round all predicted probabilities to **1% precision** (nearest 0.01). Prevents model reconstruction attack (per PITFALLS.md) and avoids over-precision meaningless to bettors.
- **D-09:** Hit rates include both rate and sample count per window: `{L5: {rate: 0.8, count: 5}, L10: {rate: 0.7, count: 10}, L20: {rate: 0.65, count: 20}, season: {rate: 0.68, count: 55}}`. Sample count lets frontend show "4/5 L5" and de-emphasize small samples.

### Edge Case Behavior
- **D-10:** Model artifact not loaded -> return 200 with empty/null predictions. Player, team, and game-log endpoints still work. Graceful degradation, not a 503 error.
- **D-11:** Insufficient data (<5 games in a window) -> return `None` for that hit rate window. Clear signal that data is insufficient, not misleading numbers.
- **D-12:** Unknown player_id -> 404 Not Found with `{"detail": "Player not found"}`.

### Feature Serving Strategy
- **D-13:** Use **pre-computed features from Parquet** for predictions. When a prediction is requested, look up the player's most recent feature row from `features.parquet` filtered by player_id and stat_type. No on-the-fly feature computation per PITFALLS.md anti-pattern warning. Fast (~5ms inference), consistent with training data.
- **D-14:** If features.parquet doesn't contain a row for a player (e.g., not enough games), the prediction endpoint returns no prediction for that player (graceful skip, not error).

### API URL Structure
- **D-15:** Flat `/api` prefix with resource-based routes. No versioning prefix for V2. Endpoints: `/api/players`, `/api/players/{id}/props`, `/api/players/{id}/gamelogs`, `/api/players/{id}/hitrates`, `/api/players/{id}/lines`, `/api/teams`, `/api/health`.

### Health & Model Status
- **D-16:** `/health` endpoint returns model status alongside service health: `{"status": "healthy", "service": "HoopProphet API", "version": "2.0.0", "model_loaded": true}`. Useful for monitoring and debugging.

### the agent's Discretion
- Exact FastAPI dependency injection pattern for services
- Internal service class structure (PlayerService, TeamService, HitRateService, PredictionService)
- Pydantic response model definitions for each endpoint
- Error logging format and verbosity
- SQLite connection management (per-request vs pooled)
- Feature row lookup implementation in PredictionService

### Folded Todos
(No pending todos were folded into scope.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — PROP-01 through PROP-06 (hit rates, default lines, top props, ML probability, game logs), CLNP-02 (model artifact loading), CLNP-03 (SQLite cache serving)
- `.planning/ROADMAP.md` — Phase 5 goal, success criteria, and requirements mapping
- `.planning/PROJECT.md` — Key decisions: binary classification, unified model, offline training, no Gemini

### Research (pitfalls & architecture)
- `.planning/research/PITFALLS.md` — Pitfall #5 (NBA API rate limiting: serve from cache, no live calls), performance trap "Computing features on-the-fly per prediction request", security: "round probabilities to nearest 1% to prevent model reconstruction"
- `.planning/research/ARCHITECTURE.md` — Current V1 architecture, FastAPI pattern, Pydantic models, data flow
- `.planning/research/STACK.md` — FastAPI, Pydantic, LightGBM, pandas, SQLite, uvicorn

### Phase 3-4 outputs (model artifact & features)
- `server/pipeline/artifact.py` — `load_artifact()` and `predict_proba()` for model serving
- `server/pipeline/train_config.py` — `MODEL_ARTIFACT_PATH`, `MODEL_DIR`, feature column contracts
- `server/pipeline/feature_config.py` — `ALL_TARGET_STATS`, `PRIMARY_STATS`, `STAT_TYPE_MAP`, `WINDOWS_PRIMARY`, `MIN_GAMES_PER_SEASON`, `N_THRESHOLD_LINES`
- `server/pipeline/features.py` — `run_feature_pipeline()` Parquet output contract
- `server/data/features.parquet` — Pre-computed feature matrix (source of truth for prediction features)

### Phase 1-2 outputs (data & queries)
- `server/pipeline/db/queries.py` — `get_players_df()`, `get_teams_df()`, `get_game_logs_df()` for SQLite query patterns
- `server/pipeline/db/schema.py` — SQLite table definitions (player_game_logs, teams, players, team_stats)
- `server/pipeline/__init__.py` — `SEASONS`, `DATA_DIR`, `DB_PATH`

### Prior phase contexts (locked decisions)
- `.planning/phases/01-data-pipeline-caching/01-CONTEXT.md` — SQLite cache, no live NBA API calls, DNP synthesis
- `.planning/phases/03-model-training-calibration/03-CONTEXT.md` — Unified LightGBM, binary classification, isotonic/Platt calibration, single .joblib artifact
- `.planning/phases/04-back-testing-engine/04-CONTEXT.md` — Walk-forward backtest, JSON+Parquet output, -110 vig

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/pipeline/artifact.py` — `load_artifact()` and `predict_proba()`: production artifact loading for the model serving endpoint
- `server/pipeline/db/queries.py` — `get_players_df()`, `get_teams_df()`, `get_game_logs_df()`: existing SQLite query functions for player/team/game-log data
- `server/pipeline/feature_config.py` — `ALL_TARGET_STATS`, `PRIMARY_STATS`, `STAT_TYPE_MAP`, `WINDOWS_PRIMARY`: constants defining stats, windows, and target generation
- `server/pipeline/train_config.py` — `MODEL_ARTIFACT_PATH`, `LGBM_PARAMS`, `LEAKAGE_COLUMNS`: model config and artifact path
- `server/app.py` — FastAPI app structure, CORS middleware, Pydantic models: V1 patterns to replace (not extend)

### Established Patterns
- FastAPI with Pydantic request/response models for API validation
- SQLite `INSERT OR IGNORE` for idempotent inserts, `SELECT` queries via pandas DataFrames
- Pipeline uses `server/pipeline/` package structure with `collectors/`, `processors/`, `db/` subpackages
- `logging` module for structured logging (pipeline), `print()` with emojis in V1 app.py (to be replaced)
- Test pattern: pytest with in-memory SQLite and seed data in `server/tests/`
- `tqdm` for progress bars, `tenacity` for retries

### Integration Points
- New API routers connect to SQLite via existing `queries.py` functions — no new DB layer needed
- PredictionService reads from `features.parquet` for pre-computed feature rows — same file Phase 2 produces
- Model artifact loaded once at FastAPI lifespan startup via `load_artifact()` — stored on `app.state`
- V1 `server/ml/` modules are NOT imported — replaced entirely by V2 services and cached data
- V1 `server/app.py` endpoints (`/predict`, `/prop-line`) are removed and replaced by new V2 routers

</code_context>

<specifics>
## Specific Ideas

- Default lines should feel "sportsbook-like" — median-based, rounded to 0.5, matching how actual NBA props are set
- Top props should surface what a player is "known for" — a guard's assists, not their blocks
- Hit rate windows need sample sizes alongside rates — "4/5 L5" means more than "80% L5" when bettors need to know how reliable that number is
- Probability rounding to 1% is both practical (bettors don't need 0.71847) and a security measure against model reconstruction
- Graceful degradation is critical: if the model isn't loaded, the API still serves players, teams, and game logs — just no predictions

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-api-layer-prop-serving*
*Context gathered: 2026-04-18*