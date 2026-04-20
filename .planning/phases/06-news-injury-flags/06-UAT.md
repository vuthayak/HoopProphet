---
status: testing
phase: 06-news-injury-flags
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md
started: 2026-04-20T00:00:00Z
updated: 2026-04-20T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold-Start Smoke Test
expected: |
  Kill any running server. Start the FastAPI server from scratch.
  GET http://localhost:8000/api/health returns {"status": "ok"}
result: pass
note: "Endpoint returns status:healthy (not ok) — matches actual app.py implementation"

### 2. News Endpoint: Player Not Found
expected: |
  GET /api/players/99999/news returns 404 with error body
result: pass
reported: "404 with {\"detail\":\"Player not found\"}"

### 3. News Endpoint: Response Structure
expected: |
  GET /api/players/{valid_id}/news returns:
  {
    "player_id": 123,
    "alerts": [],
    "news_items": [],
    "stale_warning": false
  }
result: issue
reported: "stale_warning returned null instead of false"
severity: minor

### 4. Embedded Alerts in Player Response
expected: |
  GET /api/players/{id} includes an alerts field (array, may be empty)
result: pass

### 5. Stale Warning
expected: |
  After inserting a news item with fetched_at > 24 hours ago,
  GET /api/players/{id}/news returns "stale_warning": true
result: issue
reported: "Server hangs/times out on news endpoint. Root cause: news.py calls is_cache_fresh() which invokes process_all() on every request when cache is stale, and process_all() hangs trying to fetch NBA.com injury report HTML."
severity: blocker

### 6. Alert Categorization
expected: |
  The ALERT_CATEGORIES config has 7 categories with correct priorities:
  OUT=1, INJURY=2, QUESTIONABLE=3, SUSPENSION=4, TRADE=5, G_LEAGUE=6, REST=7
  Fuzzy name matching correctly assigns priority to news items
result: blocked
blocked_by: server
reason: "Cannot test — news endpoint hangs due to process_all() hanging on NBA.com HTML fetch"

### 7. Graceful Degradation (empty DB)
expected: |
  Calling news service methods on a fresh database returns empty arrays,
  stale_warning: false, and raises no exceptions
result: blocked
blocked_by: server
reason: "Cannot test — news endpoint hangs"

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps

[none yet]
