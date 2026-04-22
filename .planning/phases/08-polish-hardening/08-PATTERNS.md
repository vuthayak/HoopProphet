# Phase 8 Pattern Map: Polish & Hardening

**Phase:** 08-polish-hardening

## Files to Create/Modify

| File | Role | Closest Analog | Pattern Source |
|------|------|---------------|----------------|
| `server/ml/` (directory) | V1 dead code (DELETE) | N/A — entire directory removed | D-01 |
| `server/data/nba.db` | V1 remnant (DELETE) | N/A — 0-byte file | D-03 |
| `docker-compose.yml` | Docker config (MODIFY) | Existing file, remove GEMINI_API_KEY line | D-07 |
| `server/app.py` | CORS middleware (MODIFY) | Lines 55-60, tighten allow_methods | D-08 |
| `server/tests/test_integration_05.py` | V1 cleanup test (EXTEND) | Existing TestV1Cleanup class at line 438 | D-12, D-13 |
| `hoopprophet/.gitignore` | Git ignore (MODIFY) | Currently only has `/build` old CRA pattern | D-04 |
| `.gitignore` | Root git ignore (MODIFY) | Already has `__pycache__/` at line 4 but tracked files remain | D-05 |
| `hoopprophet/Dockerfile` | Docker config (VERIFY — already fixed in 07-05) | `serve -s dist -l 3000 --single` | D-11 |
| `docker-compose.yml` | Docker compose (VERIFY — clean start after D-07) | Remove GEMINI_API_KEY, verify services up | D-14 |

## Established Codebase Patterns

### V2 API Structure
- `server/app.py` — FastAPI app with lifespan model preloading, CORS middleware, V2 routers
- `server/api/` — V2 API routers (players, teams, news, backtest)
- `server/services/` — V2 service layer
- `server/pipeline/` — V2 ML pipeline (LightGBM, not XGBoost)
- `server/core/config.py` — Centralized config (DB_PATH, MODEL_ARTIFACT_PATH, CORS_ORIGINS)

### Test Patterns
- `server/tests/test_integration_05.py` — TestV1Cleanup class for V1 removal assertions
- Uses `os.path.join(os.path.dirname(__file__), "..", "requirements.txt")` for file checks
- Uses `open(path).read()` for content assertions

### Git Patterns
- Root `.gitignore` at project root
- `hoopprophet/.gitignore` for frontend-specific ignores
- Tracked `__pycache__/` files need `git rm` even though `.gitignore` covers them going forward

## Key Context: What's Already Done

- `xgboost` and `google-generativeai` already removed from `requirements.txt` (Phase 5)
- `app.py` already has no imports from `server.ml` or `nba_api.stats` (Phase 5)
- `TestV1Cleanup` class already exists in `test_integration_05.py` with 3 tests (xgboost check, google-generativeai check, app.py V1 imports check)
- Dockerfile already uses `serve --single` (Phase 7, plan 05)
- V2 API is fully functional with SQLite cache serving and model artifact preloading