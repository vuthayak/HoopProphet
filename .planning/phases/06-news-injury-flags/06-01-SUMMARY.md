---
phase: 06-news-injury-flags
plan: "01"
subsystem: news_service
tags: [news, injury, rss, cache, sqlite]
requires: [NEWS-01, NEWS-02]
provides: [news_items-table, player_alerts-table, news_service-class, alert-keyword-matching]
affects: [server/pipeline/db/schema.py, server/pipeline/db/queries.py, server/core/config.py, server/services/news_service.py, server/tests/test_news_service.py]
key-decisions:
  - "Used requests_cache CachedSession (already in requirements) for HTTP caching, matching NBAClient pattern"
  - "Used feedparser for RSS parsing (added feedparser>=6.0.0 to requirements.txt)"
  - "Fuzzy name matching: 80% token overlap threshold, diacritic normalization via unicodedata"
  - "Alert priority: OUT > INJURY > QUESTIONABLE > SUSPENSION > TRADE > G_LEAGUE > REST"
  - "Cache freshness: 6h TTL, 24h stale warning threshold"
tech-stack:
  added: [feedparser]
  patterns: [rate-limiting, tenacity-retry, cached-session, tdd]
key-files:
  created:
    - path: server/services/news_service.py
      description: NewsService with fetch_injury_report, fetch_rss, match_player_name, match_player_id, generate_alerts, is_cache_fresh, process_all
    - path: server/tests/test_news_service.py
      description: 57 tests covering schema, queries, keyword matching, and NewsService integration
  modified:
    - path: server/pipeline/db/schema.py
      description: Added news_items and player_alerts tables with indexes
    - path: server/pipeline/db/queries.py
      description: Added insert/get/cleanup functions for news_items and player_alerts
    - path: server/core/config.py
      description: Added RSS URLs, TTL constants, ALERT_CATEGORIES dict
    - path: server/requirements.txt
      description: Added feedparser>=6.0.0
requirements-completed: [NEWS-01, NEWS-02]
duration: ~3 min
started: "2026-04-19T00:00:00Z"
completed: "2026-04-19T00:00:00Z"
---

# Phase 6 Plan 1: News Data Layer — Complete

System has a complete news and injury flag data layer: SQLite schema for `news_items` and `player_alerts`, `NewsService` with NBA injury report HTML parsing, RSS feed aggregation via feedparser, fuzzy player name matching with 80% token overlap, TTL-based cache freshness checking, and comprehensive TDD tests (57 total).

**Tasks:** 2 (schema+queries+config | NewsService+tests) | **Files:** 5 modified, 2 created | **Tests:** 57 passing

## What Was Built

- **news_items table**: Source, headline, raw content, timestamps, player link, alert keywords
- **player_alerts table**: Player ID, alert type, subcategory, severity, source, headline, first/last seen
- **NewsService**: Fetches NBA Official Injury Report (HTML parsing), ESPN/NBA.com RSS feeds, matches player names, generates alerts with priority-based categorization, manages TTL-based caching
- **Fuzzy name matching**: Accent normalization (Jokic→Jokić), nickname support (LeBron→LeBron James), last-name-only (Embiid→Joel Embiid), 80% token overlap threshold
- **Cache management**: 6-hour TTL, 24-hour stale warning, automatic cleanup of old news (30 days) and expired alerts (7 days)
- **Graceful degradation**: All external fetch failures caught and logged — service never crashes

## Deviations from Plan

None — plan executed exactly as written.

## Next

Ready for Plan 06-02: News API endpoints (depends on NewsService from this plan)
