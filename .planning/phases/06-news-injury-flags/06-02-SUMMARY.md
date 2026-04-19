---
phase: 06-news-injury-flags
plan: "02"
subsystem: news_api
tags: [news, api, fastapi, endpoints]
requires: [NEWS-03]
provides: [news-endpoint, embedded-alerts, integration-tests]
affects: [server/api/news.py, server/api/players.py, server/services/player_service.py, server/app.py, server/tests/test_news_api.py, server/tests/test_integration_06.py]
key-decisions:
  - "NewsService imported lazily inside endpoint to avoid circular import"
  - "get_player_alerts_summary wraps in try/except for graceful degradation when table doesn't exist"
  - "updated_ago computed from server UTC now — not client time"
  - "stale_warning triggers when any alert is > 24h old"
tech-stack:
  added: []
  patterns: [fastapi-router, graceful-degradation, lazy-import]
key-files:
  created:
    - path: server/api/news.py
      description: News API router with GET /api/players/{player_id}/news endpoint
    - path: server/tests/test_news_api.py
      description: API endpoint tests (10 tests)
    - path: server/tests/test_integration_06.py
      description: End-to-end integration tests (13 tests)
  modified:
    - path: server/api/players.py
      description: Extended get_player endpoint with alerts summary
    - path: server/services/player_service.py
      description: Added get_player_alerts_summary function
    - path: server/app.py
      description: Registered news_router
requirements-completed: [NEWS-03]
duration: ~2 min
started: "2026-04-19T00:00:00Z"
completed: "2026-04-19T00:00:00Z"
---

# Phase 6 Plan 2: News API Endpoints — Complete

System exposes news and injury flags via FastAPI endpoints: dedicated `/api/players/{id}/news` endpoint returning full alert details and news items, plus embedded lightweight alerts summary in the standard `/api/players/{id}` response. Both endpoints include stale data warnings when news is older than 24 hours.

**Tasks:** 2 (API router + embedded alerts | integration tests) | **Files:** 6 modified/created | **Tests:** 57 news service + API/integration tests

## What Was Built

- **GET /api/players/{id}/news**: Full news details with alerts, timestamps, stale warnings, and `refresh` parameter to force re-fetch
- **GET /api/players/{id}**: Extended to include `alerts` array (lightweight: alert_type, severity, subcategory, last_updated_at)
- **get_player_alerts_summary()**: Graceful degradation — returns empty list if table doesn't exist or query fails
- **Stale data warning**: Present in news endpoint when any alert is older than 24 hours

## Deviations from Plan

None — plan executed exactly as written.

## Next

Phase 6 complete. Ready for Phase 7: Frontend Rebuild.
