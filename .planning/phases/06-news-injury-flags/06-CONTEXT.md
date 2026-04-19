# Phase 6: News & Injury Flags - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

System searches for and finds player news matching injury/trade/arrest/availability keywords, then flags players with active alerts (type, source, recency) so bettors don't wager on unavailable players. News flags are accessible via API for display on player pages. This is keyword-based search — not full NLP sentiment analysis (out of scope per PROJECT.md).

</domain>

<decisions>
## Implementation Decisions

### News Source Selection
- **D-01:** Use **NBA Official Injury Report** as the primary authoritative source for player availability (probable/questionable/doubtful/out designations). Updated daily, official, and includes player IDs for reliable matching.
- **D-02:** Supplement with **RSS feeds from ESPN and NBA.com** for broader coverage beyond injuries: trades, suspensions, G League assignments, rest days. Covers categories the injury report doesn't.
- **D-03:** No paid APIs (per PROJECT.md constraint). No web scraping — too fragile and maintenance-heavy for a small team.

### Search & Matching Strategy
- **D-04:** Use **player ID cross-reference** when the source provides one (NBA injury report includes player IDs). This is the most reliable matching path.
- **D-05:** Fall back to **name matching** for sources without IDs (RSS feeds). Match against the `players` table `full_name` field with fuzzy matching for common variations (accents, nicknames, shortened names like "Jokic" → "Nikola Jokić").

### Alert Freshness & Recency
- **D-06:** Cache news results with a **TTL of 4-6 hours**. Re-fetch when cache is stale. Balances freshness with API rate limits — the NBA injury report only updates once daily anyway.
- **D-07:** Show **"Updated X min/hours ago" timestamps** on each alert so bettors can judge reliability.
- **D-08:** Display a **stale data warning** if news is older than 24 hours. Bettors see the data age and can decide whether to trust it.

### API Endpoint Design
- **D-09:** Provide **both** a dedicated endpoint and an embedded summary:
  - `/api/players/{id}/news` — full alert details (news items, sources, timestamps, alert type, severity, raw headline/URL)
  - Embedded `alerts` array in existing `/api/players/{id}` response — lightweight summary (alert_type, last_updated) for badge/flag display without extra requests
- **D-10:** No separate `/api/news` top-level endpoint — news is always scoped to a player. Consistent with Phase 5's resource-based URL pattern.

### Alert Categories & Severity
- **D-11:** Use **bettor-actionable alert categories**: INJURY, OUT, QUESTIONABLE, TRADE, SUSPENSION, G_LEAGUE, REST. Simple, meaningful, and immediately tells bettors whether to worry.
- **D-12:** Preserve NBA official status designations when available (probable/questionable/doubtful/out) as subcategories within INJURY. An "OUT" alert is a hard stop; "QUESTIONABLE" means proceed with caution.

### News Data Storage
- **D-13:** Store **both raw news items and derived player flags** in SQLite alongside existing tables:
  - `news_items` table: source, headline, URL, published_at, fetched_at, raw_content keyword match
  - `player_alerts` table: player_id (FK to players), alert_type, severity, source, source_url, first_seen_at, last_updated_at
- **D-14:** Raw news items are retained so bettors can see *why* a player is flagged (e.g., "Questionable - right knee soreness, per NBA injury report"). This is the evidentiary link between a flag and its source.

### the agent's Discretion
- Exact RSS feed parsing implementation (feedparser library, custom XML parser, etc.)
- Fuzzy matching algorithm and threshold (Levenshtein distance, rapidfuzz, or simple tokenization)
- SQLite schema details for `news_items` and `player_alerts` tables
- TTL refresh mechanism (background thread, on-demand cache invalidation, or scheduled job)
- Keyword lists for each alert category (these will evolve over time)
- Pydantic response model definitions for news endpoints
- Error handling for unavailable sources (source down, malformed feed)

### Folded Todos
(No pending todos were folded into scope.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — NEWS-01 (keyword search for injury/trade/arrest/availability), NEWS-02 (flag players with alert type, source, recency), NEWS-03 (news flags on player page via API)
- `.planning/ROADMAP.md` — Phase 6 goal, success criteria, and requirements mapping
- `.planning/PROJECT.md` — Key decisions: keyword-based search (not full NLP), no paid APIs, no user accounts

### Research docs
- `.planning/research/PITFALLS.md` — Pitfall #2 (survivor bias: DNP rows, injury context), Pitfall #5 (NBA API rate limiting: cache, don't call live)

### Phase 5 outputs (API layer to extend)
- `server/api/players.py` — Player router with existing `/api/players` and `/api/players/{id}` endpoints — news alerts will be embedded here
- `server/services/player_service.py` — PlayerService for SQLite queries — extend with alert lookups
- `server/core/config.py` — Centralized config (DB_PATH, DATA_DIR, MODEL_ARTIFACT_PATH) — add news source config here
- `server/app.py` — FastAPI app structure (lifespan, CORS, router registration)

### Phase 1 outputs (data patterns)
- `server/pipeline/db/schema.py` — SQLite table definitions pattern — news_items and player_alerts tables follow this pattern
- `server/pipeline/db/queries.py` — SQLite query pattern — extend with news/alert queries
- `server/pipeline/db/connection.py` — SQLite connection management (WAL mode)
- `server/pipeline/nba_client.py` — Rate-limited, cached HTTP client pattern — reuse for RSS feed fetching

### Prior phase contexts (locked decisions)
- `.planning/phases/05-api-layer-prop-serving/05-CONTEXT.md` — Flat /api routes, lean JSON, graceful degradation, 1% probability rounding
- `.planning/phases/01-data-pipeline-caching/01-CONTEXT.md` — SQLite caching, no live NBA API calls per request, resumable collection with progress tracking
- `.planning/phases/03-model-training-calibration/03-CONTEXT.md` — Unified LightGBM, single .joblib artifact

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/pipeline/nba_client.py` — NBAClient with rate limiting, caching (requests_cache), and retry logic (tenacity): reuse pattern for RSS feed fetching
- `server/pipeline/db/schema.py` — SQLite table creation pattern (DDL strings, foreign keys, indexes): follow for news_items and player_alerts tables
- `server/pipeline/db/queries.py` — Parameterized SQL query pattern: extend for news/alert queries
- `server/pipeline/db/connection.py` — get_connection() with WAL mode: reuse for news database operations
- `server/api/players.py` — Player router and endpoints: embed alerts array in player response
- `server/services/player_service.py` — PlayerService with search_players(), get_players(): extend with alert lookup methods
- `server/core/config.py` — Centralized config: add RSS feed URLs, TTL settings, keyword config here

### Established Patterns
- FastAPI with Pydantic request/response models for API validation (Phase 5)
- SQLite for all structured data with WAL mode for concurrent reads (Phase 1)
- Rate-limited HTTP client with caching for external data sources (Phase 1)
- Pipeline CLI pattern: `python -m server.pipeline.ingest --full/--refresh` (Phase 1-3)
- `server/services/` for business logic, `server/api/` for route handlers (Phase 5)
- Graceful degradation: if external service is down, API still serves cached data (Phase 5)
- JSON metrics output and structured logging (Phase 3-4)

### Integration Points
- New `news_items` and `player_alerts` tables in the same SQLite database (`hoopprophet.db`)
- New `NewsService` in `server/services/news_service.py` — fetches, parses, and stores news from sources
- New `/api/players/{id}/news` endpoint in `server/api/players.py` (or new `server/api/news.py` router)
- Extend `server/services/player_service.py` to include `alerts` summary in player response
- Extend `server/core/config.py` with news source URLs, TTL, and search keyword config
- RSS feed fetching follows the same rate-limited, cached pattern as `NBAClient` in Phase 1

</code_context>

<specifics>
## Specific Ideas

- "Questionable" from the NBA injury report is the most bettor-relevant designation — it means the player might not play, which directly impacts prop bet outcomes
- Raw news article storage lets bettors see the original headline/source, building trust that the flag isn't just a glitch
- TTL-based caching makes the news feature resilient — if a source is temporarily down, stale cached data still serves with a "last updated" timestamp
- Player ID matching from the NBA injury report is the most reliable path — it eliminates the name-matching ambiguity entirely for the most authoritative source

</specifics>

<deferred>
## Deferred Ideas

- Full NLP sentiment analysis for news articles — explicitly out of scope per PROJECT.md ("keyword-based flagging is sufficient for V2")
- Automated betting recommendations based on news flags — future consideration, not this phase
- Push notifications or real-time alerts — this phase is API-only; push is a frontend feature for Phase 7+
- Sportsbook odds comparison — deferred to a future milestone per PROJECT.md

</deferred>

---

*Phase: 06-news-injury-flags*
*Context gathered: 2026-04-19*