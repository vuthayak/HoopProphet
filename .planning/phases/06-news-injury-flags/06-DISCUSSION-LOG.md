# Phase 6: News & Injury Flags - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-19
**Phase:** 06-news-injury-flags
**Mode:** interactive discuss

## Areas Discussed

1. News Source Selection
2. Search & Matching Strategy
3. Alert Freshness & Recency
4. API Endpoint Design
5. Alert Categories & Severity
6. News Data Storage

## Q&A Record

### News Source Selection
- **Q:** Which free news sources should Phase 6 search for player availability information?
- **Options:** NBA Injury Report only / NBA Injury Report + RSS feeds / Web scraping (broadest)
- **Answer:** NBA Injury Report + RSS feeds
- **Rationale:** Injury report is authoritative for availability, RSS feeds cover broader categories (trades, suspensions). No paid APIs per PROJECT.md constraint.

### Search & Matching Strategy
- **Q:** How should news items be matched to players in the database?
- **Options:** Exact name + fuzzy fallback / Player ID when available, name match otherwise / Keyword proximity search
- **Answer:** Player ID when available, name match otherwise
- **Rationale:** Most reliable matching for the authoritative source (injury report has player IDs), flexible fallback for RSS feeds.

### Alert Freshness — Caching
- **Q:** How should news data freshness be handled?
- **Options:** Cached with TTL + recency display / Real-time fetch every request / Background refresh job
- **Answer:** Cached with TTL + recency display
- **Rationale:** NBA injury report updates once daily; TTL caching balances freshness with rate limits. Staleness is visible to bettors.

### Alert Freshness — Recency Display
- **Q:** How should recency be communicated to bettors?
- **Options:** Timestamps + stale warning / Auto-dismiss old alerts / Date only
- **Answer:** Timestamps + stale warning
- **Rationale:** Bettors need to judge reliability themselves. Timestamps show when data was last confirmed fresh; stale warning flags old data.

### API Endpoint Design
- **Q:** How should news flags be exposed via the API?
- **Options:** Dedicated endpoint + embed in player / Separate endpoint only / Embed in player only
- **Answer:** Dedicated endpoint + embed in player
- **Rationale:** Lightweight alerts summary in player response for badge display (no extra request), dedicated /news endpoint for full details.

### Alert Categories
- **Q:** How should news alerts be categorized?
- **Options:** Bettor-actionable categories / Binary: available vs flagged / Full NBA status taxonomy
- **Answer:** Bettor-actionable categories
- **Rationale:** INJURY, OUT, QUESTIONABLE, TRADE, SUSPENSION, G_LEAGUE, REST — immediately tells bettors whether to worry. Preserves NBA official designations as subcategories.

### News Data Storage
- **Q:** Should Phase 6 store raw news articles or just derived flags?
- **Options:** Raw news + derived flags / Derived flags only
- **Answer:** Raw news + derived flags
- **Rationale:** Raw news items provide evidentiary context — bettors can see *why* a player is flagged. Both stored in SQLite alongside existing tables.

## Deferred Ideas

- Full NLP sentiment analysis — out of scope per PROJECT.md
- Automated betting recommendations — future consideration
- Push notifications — API-only this phase, frontend is Phase 7+
- Sportsbook odds comparison — deferred milestone per PROJECT.md