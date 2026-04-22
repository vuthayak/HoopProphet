# Phase 8: Polish & Hardening - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove V1 technical debt and production-ready cleanup. The Gemini AI summary dependency is fully removed (CLNP-01), all deprecated V1 code paths are eliminated, Docker Compose runs cleanly with no V1 remnants, and the application is production-ready. The phase also folds in the incomplete Phase 7 plan 07-05 (SPA routing fallback fix) as a deployment polish item.

</domain>

<decisions>
## Implementation Decisions

### V1 Code Removal
- **D-01:** Delete entire `server/ml/` directory — including `model_train.py` (Gemini import + XGBoost), `dataset.py` (live NBA API calls), `prop_line.py` (live NBA API calls), and `__pycache__/`. No V2 code references `server/ml/`.
- **D-02:** Conduct a full V2 codebase audit for any remaining V1 imports or references — grep for `xgboost`, `google.generativeai`, `from server.ml`, `gemini`, `GEMINI_API_KEY`, `react-scripts`, `@mui`, `@material-ui`. Remove or replace any found.
- **D-03:** Delete `server/data/nba.db` (0-byte V1 remnant). Keep `server/data/nba_cache.sqlite` (V2 requests_cache) and `server/data/hoopprophet.db` (V2 SQLite).

### Git & Build Hygiene
- **D-04:** `git rm` the tracked `hoopprophet/dist/` files (Vite build output committed to git). Add `/dist` to `hoopprophet/.gitignore` (currently only has `/build` for CRA).
- **D-05:** Add `**/__pycache__/` to root `.gitignore`. Remove tracked `__pycache__/` files from `server/ml/` (deleted as part of D-01).
- **D-06:** Audit and clean any other tracked build artifacts or stale files in git that don't belong (beyond dist/ and __pycache__).

### Docker & Deployment Hardening
- **D-07:** Remove `GEMINI_API_KEY=${GEMINI_API_KEY}` from `docker-compose.yml` environment variables.
- **D-08:** Tighten CORS in `server/app.py`: restrict `allow_methods` to `["GET", "POST"]` only (currently `["*"]`). Remove `allow_credentials=True` unless needed (currently set but no auth uses cookies).

### Error Response Audit
- **D-09:** Audit all V2 API endpoints for error information leakage. Ensure error responses return generic messages to clients (e.g., "Prediction failed. Please try again.") with detailed logging server-side only. No `str(e)` in HTTP responses.

### Dead Code Sweep
- **D-10:** After server/ml/ removal, do a broader dead code audit across the V2 codebase: unused imports, commented-out code blocks, unreachable code paths, stale `.env` references. Remove what's found.

### Folding Phase 7 Plan 07-05
- **D-11:** Fold the incomplete Phase 7 plan 07-05 (SPA routing fallback fix — serve `--single` flag) into Phase 8. It's a deployment polish item that naturally belongs here.

### Test & Validation
- **D-12:** Extend `test_integration_05.py`'s `TestV1Cleanup` class to assert: `server/ml/` directory doesn't exist, no `GEMINI_API_KEY` in docker-compose.yml, no `google-generativeai` or `xgboost` import anywhere in the codebase, no V1 code paths reachable from V2.
- **D-13:** Add a broader audit validation: grep/assert that no dead V1 imports exist anywhere in V2 codebase (xgboost, gemini, from server.ml, etc.). This is the "full audit validation suite" approach.
- **D-14:** Docker Compose smoke test: verify the app starts cleanly with no V1 code paths or missing dependencies.

### the agent's Discretion
- Exact implementation of CORS tightening (which origins to allow in production vs development)
- How to structure the audit grep patterns (bash script vs test assertions)
- Log format standardization (V2 already uses Python logging; no changes needed)
- Whether to add Docker HEALTHCHECK instructions (not required by this phase)

### Folded Todos
- Phase 7 Plan 07-05 (SPA routing fallback) — folded in as D-11

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — CLNP-01 (remove Gemini AI summary dependency from backend), CLNP-02 (replace per-request model training with artifact loading — completed in Phase 5), CLNP-03 (API serves player/team lists from SQLite cache — completed in Phase 5)
- `.planning/ROADMAP.md` — Phase 8 goal, success criteria, and requirements mapping
- `.planning/PROJECT.md` — Key decisions: "Drop Gemini summaries" (pending), "No paid APIs", offline training pipeline

### Codebase concerns
- `.planning/codebase/CONCERNS.md` — Comprehensive audit of V1 tech debt: dual ML systems, model training per request, Gemini API key without validation, debug print statements, overly permissive CORS, error details leaked to clients, unpinned dependencies, no frontend error boundaries

### Prior phase contexts (locked decisions)
- `.planning/phases/05-api-layer-prop-serving/05-CONTEXT.md` — Flat /api routes, lean JSON, 1% probability rounding, graceful degradation, model artifact loaded at startup
- `.planning/phases/07-frontend-rebuild/07-CONTEXT.md` — Vite + React 19 + Tailwind v4 rebuild, delete all V1 frontend code, dark-mode-only, component-based architecture

### V1 code to remove
- `server/ml/model_train.py` — Gemini import (line 19), GEMINI_API_KEY usage (lines 168-173), XGBoost (line 4)
- `server/ml/dataset.py` — Live NBA API calls, no caching, right-join data leakage bug
- `server/ml/prop_line.py` — Live NBA API calls, IndexError for empty DataFrames
- `server/ml/__pycache__/` — 6 stale .pyc files tracked in git
- `docker-compose.yml` — GEMINI_API_KEY env var (line 10)

### Docker & deployment
- `docker-compose.yml` — Backend + frontend service definitions
- `server/Dockerfile` — Python 3.11-slim, uvicorn entrypoint
- `hoopprophet/Dockerfile` — Multi-stage Vite build + serve

### Testing
- `server/tests/test_integration_05.py` — Existing TestV1Cleanup class for V1 removal assertions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/app.py` — V2 FastAPI app with lifespan model preloading, CORS middleware, V2 routers. Clean, no V1 imports.
- `server/api/` — V2 API routers (players, teams, news, backtest). Fully functional.
- `server/services/` — V2 service layer. Fully functional.
- `server/pipeline/` — V2 ML pipeline (LightGBM, not XGBoost). Fully functional.
- `server/tests/test_integration_05.py` — TestV1Cleanup class already checks xgboost/gemini removal from requirements.txt and app.py. Extend for this phase.

### Established Patterns
- V2 API uses `server/api/` routers (not `server/app.py` monolithic endpoints)
- V2 frontend uses Vite + React 19 + Tailwind v4 (not CRA + MUI)
- V2 model serving uses pre-loaded artifact (not per-request training)
- V2 data access uses SQLite cache (not live NBA API calls)
- CORS currently allows all methods and headers from localhost:3000 and frontend:3000

### Integration Points
- `docker-compose.yml` — Remove GEMINI_API_KEY, verify services start cleanly
- `hoopprophet/dist/` — Remove from git tracking, add to .gitignore
- `server/Dockerfile` — Entry point uses `app:app` module path (works via WORKDIR but could be clearer)
- V2 frontend (`hoopprophet/src/`) — No references to V1 code expected, but audit confirms this

</code_context>

<specifics>
## Specific Ideas

- Clean slate approach: delete server/ml/ entirely rather than surgically removing Gemini references. The entire directory is V1 dead code.
- Full audit validation ensures no zombie references to V1 code paths remain — grep/pattern assertions that catch future regressions too.
- SPA routing fallback (07-05) is a natural fit for this phase — it's about making the Docker deployment work correctly for client-side routing.

</specifics>

<deferred>
## Deferred Ideas

- Docker HEALTHCHECK instructions — nice-to-have for production but not required for this phase
- Dependency version pinning (brewing concern in CONCERNS.md but not in scope for CLNP-01)
- Rate limiting / API key authentication — security concern flagged in CONCERNS.md but out of scope for this phase
- V2 logging audit — user decided V2 logging is fine as-is
- Daily picks dashboard — v2 requirement (PICK-01/02/03), separate phase

### Reviewed Todos (not folded)
(No todos were reviewed but not folded.)

</deferred>

---

*Phase: 08-polish-hardening*
*Context gathered: 2026-04-22*