---
status: partial
phase: 05-api-layer-prop-serving
source:
  - .planning/phases/05-api-layer-prop-serving/05-01-SUMMARY.md
  - .planning/phases/05-api-layer-prop-serving/05-02-SUMMARY.md
  - .planning/phases/05-api-layer-prop-serving/05-03-SUMMARY.md
started: 2026-04-18T10:15:00Z
updated: 2026-04-22T01:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: |
  Start the API server from scratch (no pre-existing process). Verify it starts without errors.
  Confirm /api/health responds and shows model_loaded status (may be false if no model artifact).
result: pass

### 2. /api/health Endpoint
expected: |
  GET /api/health returns JSON with model_loaded boolean field.
  Should return quickly without errors.
result: pass

### 3. /api/players List
expected: |
  GET /api/players returns a list of players.
  Should support ?search= query parameter for filtering.
  Response should be JSON array.
result: blocked
blocked_by: prior-phase
reason: "Database empty - no player data ingested yet"

### 4. /api/players/{id} with Default Lines
expected: |
  GET /api/players/{id} returns player detail with a default_lines object containing stat lines.
  Should include fields like pts, reb, ast with numeric values.
result: skipped
reason: "Database empty - requires ingested data (prior-phase)"

### 5. /api/players/{id}/props
expected: |
  GET /api/players/{id}/props returns top props with ML probability and hit rates.
  Should be an array with stat, line_value, predicted_proba, hit_rate fields.
result: skipped
reason: "Database empty - requires ingested data (prior-phase)"

### 6. /api/players/{id}/hitrates
expected: |
  GET /api/players/{id}/hitrates returns hit rates for different windows (L5, L10, L20, season).
  Should include sample counts per window.
result: skipped
reason: "Database empty - requires ingested data (prior-phase)"

### 7. /api/players/{id}/gamelogs
expected: |
  GET /api/players/{id}/gamelogs returns recent game logs.
  Should support ?limit= query parameter.
result: skipped
reason: "Database empty - requires ingested data (prior-phase)"

### 8. /api/teams List
expected: |
  GET /api/teams returns a list of teams.
  Response should be JSON array.
result: blocked
blocked_by: prior-phase
reason: "Database empty - no team data ingested yet"

### 9. /api/teams/{id}
expected: |
  GET /api/teams/{id} returns team detail for a valid team ID.
  Should return 404 for unknown team ID.
result: blocked
blocked_by: prior-phase
reason: "Database empty - no team data ingested yet"

### 10. V1 Dependencies Removed
expected: |
  requirements.txt should NOT contain xgboost or google-generativeai.
  app.py should NOT import from server.ml, nba_api.stats, or google.generativeai.
result: pass

### 11. Full Test Suite
expected: |
  Run: python -m pytest server/tests/test_integration_05.py -v
  All 37 integration tests should pass.
result: pass

## Summary

total: 11
passed: 4
issues: 0
pending: 0
skipped: 4
blocked: 3

## Gaps

[none — blocked tests require Phase 1 data ingest to populate database with real NBA players/teams/game_logs]

## Notes

Database has only 1 test player (no real NBA data). Tests 3-9 are blocked because Phase 1 completed schema setup but ingest --full was not run. These tests are valid and would pass once `python -m server.pipeline.ingest --full` populates the database.
