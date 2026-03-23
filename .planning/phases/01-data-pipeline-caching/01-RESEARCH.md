# Phase 1: Data Pipeline & Caching - Research

**Researched:** 2026-03-22
**Domain:** NBA API data collection, SQLite caching, resumable pipeline
**Confidence:** HIGH

## Summary

Phase 1 builds the data foundation: a multi-season NBA data collection and caching layer that stores game logs, team stats, and synthesized DNP rows in SQLite. The `nba_api` library (1.11.4) provides all needed endpoints — `PlayerGameLog` with `SeasonAll.all` for bulk extraction, `LeagueDashTeamStats` with `measure_type="Advanced"` for defensive rating/pace, `CommonTeamRoster` for roster membership, and `LeagueGameFinder` for team schedules. These endpoints are unofficial and undocumented, requiring aggressive caching, exponential backoff with jitter, and resumable progress tracking.

The key architectural decision is a **dual-layer caching strategy**: `requests-cache` (SQLite-backed `CachedSession`) injected into `nba_api` via `NBAHTTP.set_session()` for HTTP-level caching, plus a **structured SQLite database** for queryable game logs, team stats, and derived data. The HTTP cache prevents re-fetching completed games (box scores are immutable after finalization). The structured database enables offline queries for feature engineering downstream.

**Primary recommendation:** Build a CLI-driven data collection script (`server/pipeline/ingest.py`) that fetches data in player-by-player batches with per-player/season progress tracking in SQLite. Use `tenacity` for retry logic with exponential backoff + jitter (base 600ms, max 30s). Cross-reference `CommonTeamRoster` × `LeagueGameFinder` to synthesize zero-minute DNP rows.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Collect 5 seasons of historical data (~2020-2025) for all data types
- **D-02:** Collect data for all 450+ active NBA players, not just high-usage players — completeness for search and model training
- **D-03:** Apply sample weighting with recency decay during model training (Phase 3) so older games count less — prevents stale data from dominating predictions while preserving pattern-learning value of historical depth
- **D-04:** Researcher should investigate optimal decay rate/half-life for sample weighting in sports ML contexts

### Claude's Discretion
- Collection workflow: CLI script vs Docker service vs manual trigger
- Progress visibility and monitoring during bulk collection
- Data refresh strategy (nightly, on-demand, etc.)
- SQLite schema design and table structure
- NBA API rate limiting strategy (backoff timing, retry counts)
- DNP row synthesis approach (how to identify and create zero-minute rows)
- Data validation and completeness checks

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | System collects multi-season NBA game logs for all active players and caches in SQLite | `PlayerGameLog` with `SeasonAll.all` for bulk extraction → structured SQLite tables; `requests-cache` for HTTP caching; `CommonTeamRoster` for active player roster per season |
| DATA-02 | System collects team stats (defensive ratings, pace) and caches in SQLite | `LeagueDashTeamStats` with `measure_type="Advanced"` returns `DEF_RATING`, `PACE`, `OFF_RATING`, `NET_RATING` per team per season |
| DATA-03 | System handles NBA API rate limits with exponential backoff and retry logic | `tenacity` library with `wait_exponential_jitter(initial=0.6, max=30)` + `stop_after_attempt(5)`; 600ms base delay between all calls |
| DATA-04 | Data fetcher is resumable — can pick up where it left off if interrupted | `collection_progress` SQLite table tracking `(entity_type, entity_id, season, status, updated_at)`; skip completed entries on restart |
| DATA-05 | System synthesizes zero-minute rows for games where a player was on the roster but did not play | Cross-reference `CommonTeamRoster` (roster membership) × `LeagueGameFinder` (team schedule) × `PlayerGameLog` (games played); gaps → synthesize zero-stat rows |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nba_api | 1.11.4 | NBA game logs, player stats, team stats, roster data | Only maintained Python wrapper for stats.nba.com; supports `SeasonAll.all` bulk extraction and `NBAHTTP.set_session()` for custom sessions. Verified via PyPI. |
| requests-cache | 1.3.1 | SQLite-backed HTTP response cache for nba_api | Drop-in `CachedSession` wraps `requests.Session`; inject into nba_api via `NBAHTTP.set_session()`. Eliminates redundant API calls. Default SQLite backend, zero infrastructure. Verified via PyPI. |
| tenacity | 9.1.2 | Retry logic with exponential backoff + jitter | Production-standard retry library. `@retry(wait=wait_exponential_jitter(...))` decorator. Cleaner than hand-rolled retry loops. Verified via PyPI. |
| pandas | ≥2.2.0 | DataFrame operations for data manipulation | Already in V1. Used for concatenating game logs, merging roster/schedule data, synthesizing DNP rows. |
| SQLite (stdlib) | 3.43+ | Structured data storage for game logs, team stats, progress tracking | Python stdlib `sqlite3` module. Zero-dependency. System has SQLite 3.43.2 available. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tqdm | ≥4.66 | Progress bars for bulk collection | Visual feedback during multi-hour data pulls (450+ players × 5 seasons) |
| logging (stdlib) | — | Structured logging replacing print() statements | All pipeline modules; replaces V1's print-based logging |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| requests-cache (SQLite) | Redis cache | Redis adds a container, is volatile by default. SQLite persists to disk, zero config. |
| tenacity | Manual retry loops | tenacity handles edge cases (jitter, stop conditions, logging) that hand-rolled loops miss |
| SQLite for structured data | Parquet files only | Parquet is great for columnar reads but lacks SQL query capability and doesn't support atomic upserts for progress tracking. SQLite better for the "resumable + queryable" requirements of Phase 1. |
| SQLite for structured data | PostgreSQL | Adds a third Docker container, needs migrations/schema management. Overkill for ~500K rows. |

**Installation:**
```bash
# Add to server/requirements.txt
nba_api==1.11.4
requests-cache==1.3.1
tenacity>=9.0.0
tqdm>=4.66.0
pandas>=2.2.0
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 additions)
```
server/
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py           # CLI entry point: orchestrates full data collection
│   ├── nba_client.py       # Centralized NBA API wrapper with rate limiting + caching
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── game_logs.py    # Player game log collection (SeasonAll bulk + per-season)
│   │   ├── team_stats.py   # Team defensive rating, pace collection
│   │   ├── rosters.py      # Team roster collection per season
│   │   └── schedules.py    # Team schedule collection via LeagueGameFinder
│   ├── processors/
│   │   ├── __init__.py
│   │   └── dnp_synthesis.py  # Cross-reference roster × schedule × gamelogs → zero-minute rows
│   └── db/
│       ├── __init__.py
│       ├── schema.py       # SQLite table definitions and migrations
│       ├── connection.py   # Thread-safe connection management
│       └── queries.py      # Reusable parameterized SQL (insert, upsert, select)
├── data/
│   ├── nba_cache.sqlite    # requests-cache HTTP response store
│   └── hoopprophet.db      # Structured data: game logs, team stats, rosters, progress
```

### Pattern 1: Dual-Layer Caching (HTTP + Structured)

**What:** Two separate SQLite databases — one for raw HTTP response caching (`requests-cache`), one for structured queryable data.

**When to use:** When you need both "never re-fetch the same API call" AND "query the data with SQL for downstream consumption."

**Example:**
```python
from requests_cache import CachedSession
from nba_api.stats.library.http import NBAHTTP
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.library.parameters import SeasonAll

# Layer 1: HTTP-level caching — never re-fetch completed game data
cached_session = CachedSession(
    cache_name="data/nba_cache",
    backend="sqlite",
    expire_after=None,  # NBA box scores are immutable — cache forever
    allowable_methods=["GET", "POST"],
)
NBAHTTP.set_session(cached_session)

# All nba_api calls now go through the cache
logs = playergamelog.PlayerGameLog(
    player_id=203999,
    season=SeasonAll.all
).get_data_frames()[0]

# Layer 2: Parse and store in structured SQLite
import sqlite3
conn = sqlite3.connect("data/hoopprophet.db")
logs.to_sql("player_game_logs", conn, if_exists="append", index=False)
```

### Pattern 2: Resumable Collection with Progress Tracking

**What:** Track collection status per (entity, season) in a SQLite table. On restart, query uncompleted entries and resume from there.

**When to use:** Any bulk collection job that can crash partway through (rate limits, network errors, user interrupts).

**Example:**
```python
import sqlite3

def get_remaining_work(conn: sqlite3.Connection) -> list[tuple]:
    """Return (player_id, season) pairs not yet completed."""
    cursor = conn.execute("""
        SELECT p.player_id, s.season
        FROM players p
        CROSS JOIN seasons s
        WHERE NOT EXISTS (
            SELECT 1 FROM collection_progress cp
            WHERE cp.entity_id = p.player_id
              AND cp.season = s.season
              AND cp.status = 'completed'
        )
        ORDER BY s.season, p.player_id
    """)
    return cursor.fetchall()

def mark_completed(conn: sqlite3.Connection, player_id: int, season: str):
    conn.execute("""
        INSERT OR REPLACE INTO collection_progress
        (entity_type, entity_id, season, status, updated_at)
        VALUES ('player_gamelog', ?, ?, 'completed', datetime('now'))
    """, (player_id, season))
    conn.commit()
```

### Pattern 3: Rate-Limited NBA API Client

**What:** Centralized wrapper around `nba_api` that enforces minimum delay between calls and uses tenacity for retry with exponential backoff + jitter.

**When to use:** Every NBA API interaction in the pipeline.

**Example:**
```python
import time
import logging
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type, before_sleep_log
)

logger = logging.getLogger(__name__)

class NBAClient:
    MIN_DELAY = 0.6  # 600ms minimum between calls

    def __init__(self):
        self._last_call = 0.0

    def _enforce_rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.MIN_DELAY:
            time.sleep(self.MIN_DELAY - elapsed)
        self._last_call = time.time()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.6, max=30, jitter=2),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def fetch_player_gamelog(self, player_id: int, season: str):
        self._enforce_rate_limit()
        from nba_api.stats.endpoints import playergamelog
        return playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            timeout=30,
        ).get_data_frames()[0]
```

### Anti-Patterns to Avoid

- **Fetching live data in the API request path:** V1 calls nba_api on every `/predict` request. Phase 1 establishes the cache so downstream phases never hit the live API at serve time.
- **Fixed `time.sleep(1)` without retry:** V1's pattern in `player_inactive()` crashes permanently on any error. Use tenacity with backoff + jitter.
- **No progress tracking:** V1 re-fetches everything from scratch if interrupted. The progress table enables resumption.
- **Storing data only in DataFrames (memory):** V1 holds everything in memory. SQLite persists data across runs and enables SQL queries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP response caching | Custom file-based cache for API responses | `requests-cache` with SQLite backend | Handles cache invalidation, TTL, serialization, thread safety. 2-8ms writes. |
| Retry with exponential backoff | Custom while-loop retry logic | `tenacity` decorators | Edge cases: jitter, max attempts, logging, exception filtering, callback hooks |
| Progress bars for bulk operations | Custom print-based progress tracking | `tqdm` | Handles terminal width, ETA, rate calculation, nested loops |
| SQLite connection management | Raw `sqlite3.connect()` everywhere | Context manager wrapper with WAL mode | WAL mode enables concurrent reads during writes; context manager ensures proper cleanup |
| NBA API session configuration | Per-endpoint session setup | `NBAHTTP.set_session()` once globally | Applies to all 200+ endpoints automatically |

**Key insight:** The data pipeline's complexity is in orchestration (what to fetch, in what order, how to resume), not in any single API call. Libraries handle the low-level concerns; custom code handles the NBA-specific orchestration.

## SQLite Schema Design (Recommendation)

```sql
-- Core data tables
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    position TEXT,
    team_id INTEGER,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY,
    abbreviation TEXT NOT NULL,
    full_name TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS player_game_logs (
    player_id INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    season TEXT NOT NULL,
    game_date TEXT NOT NULL,
    matchup TEXT NOT NULL,
    wl TEXT,
    min REAL DEFAULT 0,
    pts REAL DEFAULT 0,
    reb REAL DEFAULT 0,
    ast REAL DEFAULT 0,
    stl REAL DEFAULT 0,
    blk REAL DEFAULT 0,
    fg3m REAL DEFAULT 0,
    fgm REAL DEFAULT 0,
    fga REAL DEFAULT 0,
    ftm REAL DEFAULT 0,
    fta REAL DEFAULT 0,
    oreb REAL DEFAULT 0,
    dreb REAL DEFAULT 0,
    tov REAL DEFAULT 0,
    pf REAL DEFAULT 0,
    plus_minus REAL DEFAULT 0,
    is_dnp INTEGER NOT NULL DEFAULT 0,  -- 1 = synthesized zero-minute row
    PRIMARY KEY (player_id, game_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE TABLE IF NOT EXISTS team_stats (
    team_id INTEGER NOT NULL,
    season TEXT NOT NULL,
    def_rating REAL,
    off_rating REAL,
    net_rating REAL,
    pace REAL,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (team_id, season),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS team_rosters (
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    season TEXT NOT NULL,
    PRIMARY KEY (team_id, player_id, season)
);

CREATE TABLE IF NOT EXISTS team_schedules (
    team_id INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    season TEXT NOT NULL,
    game_date TEXT NOT NULL,
    matchup TEXT NOT NULL,
    wl TEXT,
    PRIMARY KEY (team_id, game_id)
);

-- Progress tracking for resumable collection
CREATE TABLE IF NOT EXISTS collection_progress (
    entity_type TEXT NOT NULL,   -- 'player_gamelog', 'team_stats', 'team_roster', 'team_schedule'
    entity_id INTEGER NOT NULL,  -- player_id or team_id
    season TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'failed'
    error_message TEXT,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (entity_type, entity_id, season)
);

-- Indexes for downstream queries
CREATE INDEX IF NOT EXISTS idx_gamelogs_season ON player_game_logs(season);
CREATE INDEX IF NOT EXISTS idx_gamelogs_date ON player_game_logs(game_date);
CREATE INDEX IF NOT EXISTS idx_gamelogs_player_season ON player_game_logs(player_id, season);
```

**Key design decisions:**
- `is_dnp` column on `player_game_logs` distinguishes real games from synthesized zero-minute rows.
- `collection_progress` table enables resumable fetching — the pipeline queries for incomplete work on restart.
- Composite primary keys prevent duplicate inserts (`INSERT OR IGNORE` pattern).
- WAL journal mode should be enabled at connection time for concurrent read performance.

## DNP Row Synthesis Approach (Recommendation)

The V1 approach (`player_inactive()` in `dataset.py`) checks each game's box score individually with `BoxScoreSummaryV2` — this is extremely slow (1 API call + 1s sleep per game per player). For 450+ players × 82 games × 5 seasons, that's ~184,000 API calls just for inactivity detection.

**Recommended approach (no extra API calls):**

1. **Collect team schedules** via `LeagueGameFinder(team_id_nullable=team_id, season_nullable=season, player_or_team_abbreviation='T')` — one call per team per season (30 teams × 5 seasons = 150 calls).
2. **Collect team rosters** via `CommonTeamRoster(team_id=team_id, season=season)` — one call per team per season (150 calls).
3. **Collect player game logs** via `PlayerGameLog(player_id=id, season=SeasonAll.all)` — one call per player (~450 calls).
4. **Cross-reference in SQLite:** For each (player, season), find the team they were rostered on. For each team game in that season, check if the player has a game log entry. Missing entries → synthesize zero-minute row.

```python
def synthesize_dnp_rows(conn: sqlite3.Connection, season: str):
    """Find roster×schedule gaps and insert zero-minute rows."""
    cursor = conn.execute("""
        SELECT tr.player_id, ts.game_id, ts.game_date, ts.matchup
        FROM team_rosters tr
        JOIN team_schedules ts ON tr.team_id = ts.team_id AND tr.season = ts.season
        WHERE tr.season = ?
          AND NOT EXISTS (
              SELECT 1 FROM player_game_logs pgl
              WHERE pgl.player_id = tr.player_id
                AND pgl.game_id = ts.game_id
          )
    """, (season,))

    dnp_rows = []
    for player_id, game_id, game_date, matchup in cursor:
        dnp_rows.append({
            "player_id": player_id, "game_id": game_id,
            "season": season, "game_date": game_date,
            "matchup": matchup, "wl": None,
            "min": 0, "pts": 0, "reb": 0, "ast": 0,
            "stl": 0, "blk": 0, "fg3m": 0, "is_dnp": 1,
            # ... all other stat columns = 0
        })
    # Bulk insert
    if dnp_rows:
        pd.DataFrame(dnp_rows).to_sql(
            "player_game_logs", conn, if_exists="append", index=False
        )
    return len(dnp_rows)
```

**Total API calls:** ~450 (player gamelogs) + 150 (team schedules) + 150 (team rosters) + 150 (team stats) = ~900 calls, vs V1's 184,000+ calls for box score checking.

**Caveat:** `CommonTeamRoster` returns the roster as of season end, not mid-season transactions. Players traded mid-season will appear on their final team's roster but may have games with their previous team. To handle this accurately:
- Collect game logs first (they include the team in the `MATCHUP` column).
- Use the `MATCHUP` column to infer which team a player was on for each game.
- For DNP synthesis, only synthesize zero-minute rows for games where the player's team (from game log context or roster) matches the schedule team.

## Common Pitfalls

### Pitfall 1: NBA API Returns Empty DataFrames Silently
**What goes wrong:** Some `nba_api` endpoints periodically return empty DataFrames without raising an exception. The pipeline inserts zero rows and marks the collection as "completed."
**Why it happens:** stats.nba.com returns `{}` or empty result sets under load, for deprecated endpoints, or for certain player/season combinations.
**How to avoid:** Validate response shape after every API call. Check `len(df) > 0` and verify expected columns exist. If empty, mark as `failed` (not `completed`) in progress table and retry later.
**Warning signs:** Row counts per season vary wildly; some players show 0 games in seasons where they played 70+.

### Pitfall 2: Rate Limiting Causes Silent Data Gaps
**What goes wrong:** The API throttles requests, returning partial data or HTTP 429/503 errors. Without proper error handling, the pipeline silently skips players and creates incomplete datasets.
**Why it happens:** stats.nba.com has undocumented rate limits. Minimum safe delay is 600ms. Cloud/Docker IPs may be blocked entirely.
**How to avoid:** Enforce 600ms minimum between all calls. Use tenacity with exponential backoff (initial=0.6s, max=30s, 5 attempts). Log all failures. Run completeness validation after collection.
**Warning signs:** `HTTPSConnectionPool Read timed out` errors; inconsistent row counts between runs.

### Pitfall 3: CommonTeamRoster Doesn't Reflect Mid-Season Trades
**What goes wrong:** DNP synthesis creates false zero-minute rows for players who were traded. Player appears on Team A's end-of-season roster but played Team A's first 40 games with Team B.
**Why it happens:** `CommonTeamRoster` returns a snapshot, not transaction history.
**How to avoid:** Use game log data (which includes `MATCHUP` with team abbreviation) as the source of truth for team membership. Only synthesize DNP rows for periods where the player was demonstrably on that team (i.e., they have other game logs with that team in the same time window).
**Warning signs:** Players with many DNP rows clustered at the start or end of a season; DNP count exceeding reasonable injury/rest expectations.

### Pitfall 4: SeasonAll.all Returns Career History, Not Just 5 Seasons
**What goes wrong:** `PlayerGameLog(season=SeasonAll.all)` returns every season the player ever played. For veterans like LeBron James, that's 20+ seasons of data — far more than the 5 seasons we want.
**Why it happens:** `SeasonAll.all` is a convenience parameter that bypasses season filtering.
**How to avoid:** Filter the returned DataFrame to the target seasons (2020-21 through 2024-25) immediately after fetching. Alternatively, make 5 separate per-season calls instead of one SeasonAll call — more API calls but simpler data handling and better progress tracking per season.
**Warning signs:** Database growing to unexpected size; 20-year veterans consuming disproportionate storage.

### Pitfall 5: Docker/Cloud IPs Blocked by NBA API
**What goes wrong:** Data collection works locally but fails when run inside Docker or on cloud VMs. The NBA API blocks certain IP ranges.
**Why it happens:** stats.nba.com has IP-based blocking for automated scrapers, and many cloud provider IP ranges are flagged.
**How to avoid:** Test data collection from the deployment environment early. Consider running initial bulk collection locally and mounting the SQLite database into Docker. For ongoing refreshes, the HTTP cache means most calls won't hit the live API anyway.
**Warning signs:** All API calls timeout or return 403 in Docker but work on the developer's machine.

## Code Examples

### Complete requests-cache + nba_api Integration
```python
# Source: requests-cache docs + nba_api PR #486
from requests_cache import CachedSession
from nba_api.stats.library.http import NBAHTTP

def setup_cached_session(cache_path: str = "data/nba_cache") -> CachedSession:
    """Configure HTTP caching for all nba_api calls."""
    session = CachedSession(
        cache_name=cache_path,
        backend="sqlite",
        expire_after=None,         # Completed games don't change
        allowable_methods=["GET", "POST"],
        stale_if_error=True,       # Serve stale cache on API errors
    )
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.nba.com/",
        "Accept-Language": "en-US,en;q=0.9",
    })
    NBAHTTP.set_session(session)
    return session
```

### Fetching Team Advanced Stats (DEF_RATING, PACE)
```python
# Source: nba_api docs + hoopR reference
from nba_api.stats.endpoints import leaguedashteamstats

def fetch_team_advanced_stats(season: str) -> pd.DataFrame:
    """Fetch team defensive rating, pace, and other advanced stats."""
    stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense="Advanced",
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
    )
    df = stats.get_data_frames()[0]
    return df[["TEAM_ID", "TEAM_NAME", "DEF_RATING", "OFF_RATING",
               "NET_RATING", "PACE", "DEF_RATING_RANK", "PACE_RANK"]]
```

### Bulk Player Game Log Collection with Progress
```python
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.library.parameters import SeasonAll

SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]

def collect_player_gamelogs(client: NBAClient, conn: sqlite3.Connection):
    """Collect game logs for all active players, with resumable progress."""
    players = get_active_players(conn)
    remaining = get_remaining_work(conn, entity_type="player_gamelog")

    for player_id, player_name in tqdm(remaining, desc="Collecting game logs"):
        try:
            df = client.fetch_player_gamelog(player_id, season=SeasonAll.all)

            if df.empty:
                logger.warning(f"Empty gamelog for {player_name} ({player_id})")
                mark_failed(conn, "player_gamelog", player_id, "all", "Empty response")
                continue

            # Filter to target seasons
            df = df[df["SEASON_ID"].str[-7:].isin(SEASONS)]

            # Store in structured database
            df["player_id"] = player_id
            df["is_dnp"] = 0
            df.to_sql("player_game_logs", conn, if_exists="append", index=False)

            mark_completed(conn, "player_gamelog", player_id, "all")

        except Exception as e:
            logger.error(f"Failed for {player_name}: {e}")
            mark_failed(conn, "player_gamelog", player_id, "all", str(e))
```

## Data Collection Workflow (Recommendation)

**CLI script triggered manually or via cron:**

```
python -m server.pipeline.ingest [--full | --refresh]

--full:    Collect all 5 seasons from scratch (first run, ~2-4 hours)
--refresh: Only fetch current season delta (subsequent runs, ~10-20 min)
```

**Collection order (respects dependencies):**
1. **Teams** — `nba_api.stats.static.teams.get_teams()` (static, no API call)
2. **Players** — `nba_api.stats.static.players.get_players()` (static, no API call)
3. **Team rosters** — `CommonTeamRoster` per team × season (150 API calls)
4. **Team schedules** — `LeagueGameFinder` per team × season (150 API calls)
5. **Team advanced stats** — `LeagueDashTeamStats(Advanced)` per season (5 API calls)
6. **Player game logs** — `PlayerGameLog` per player (450+ API calls)
7. **DNP synthesis** — SQL cross-reference, no API calls

**Estimated total API calls:** ~755 for a full 5-season pull.
**Estimated time at 600ms/call + backoff:** ~10-15 minutes for API calls + processing.

**Data refresh strategy (on-demand or nightly):**
- `--refresh` mode only fetches current season data and only for new games since last collection.
- Use `game_date` filtering: `LeagueGameFinder` with `date_from_nullable` set to last collection date.
- Re-run DNP synthesis for current season only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (not yet installed — Wave 0 gap) |
| Config file | None — needs `pyproject.toml` or `pytest.ini` |
| Quick run command | `pytest server/tests/ -x --timeout=30` |
| Full suite command | `pytest server/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Multi-season game logs stored in SQLite | integration | `pytest server/tests/test_ingest.py::test_gamelogs_stored -x` | ❌ Wave 0 |
| DATA-02 | Team stats (def rating, pace) in SQLite | integration | `pytest server/tests/test_ingest.py::test_team_stats_stored -x` | ❌ Wave 0 |
| DATA-03 | Rate limiting with exponential backoff | unit | `pytest server/tests/test_nba_client.py::test_retry_backoff -x` | ❌ Wave 0 |
| DATA-04 | Resumable fetching after interruption | unit | `pytest server/tests/test_ingest.py::test_resume_after_interrupt -x` | ❌ Wave 0 |
| DATA-05 | Zero-minute DNP rows synthesized | unit | `pytest server/tests/test_dnp_synthesis.py::test_dnp_rows_created -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest server/tests/ -x --timeout=30`
- **Per wave merge:** `pytest server/tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `server/tests/conftest.py` — shared fixtures (temp SQLite db, mock nba_api responses)
- [ ] `server/tests/test_nba_client.py` — rate limiting, retry, session injection tests
- [ ] `server/tests/test_ingest.py` — game log collection, team stats, resumable progress
- [ ] `server/tests/test_dnp_synthesis.py` — zero-minute row synthesis correctness
- [ ] `pyproject.toml` or `pytest.ini` — pytest configuration
- [ ] Framework install: `pip install pytest pytest-timeout`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-endpoint session config | `NBAHTTP.set_session()` global injection | nba_api PR #486, Jan 2025 | Can inject `CachedSession` once for all endpoints |
| `time.sleep(1)` fixed delay | `tenacity` exponential backoff + jitter | Standard practice 2024+ | Prevents thundering herd, recovers from transient failures |
| Per-player box score checking for DNP | Roster × schedule cross-reference | Optimization for V2 | Reduces ~184K API calls to ~0 for DNP detection |
| `PlayByPlayV2`, `ScoreboardV2` | V3 variants (`PlayByPlayV3`, `ScoreboardV3`) | nba_api 1.11.x | V2 endpoints deprecated; V3 recommended for new code |

**Deprecated/outdated:**
- `BoxScoreSummaryV2` for inactivity checking: replaced by roster × schedule cross-reference approach
- Unpinned `nba_api` installation: pin to 1.11.4 to prevent breaking changes from upstream

## Open Questions

1. **SeasonAll.all vs per-season calls for game logs**
   - What we know: `SeasonAll.all` returns all seasons in one call (fewer API calls) but requires client-side season filtering. Per-season calls allow per-season progress tracking.
   - What's unclear: Whether `SeasonAll.all` has a higher failure rate or returns truncated results for players with long careers.
   - Recommendation: Use per-season calls (5 calls per player) for better progress tracking and smaller response sizes. The HTTP cache makes repeat calls cheap.

2. **`LeagueDashTeamStats` "Advanced" parameter name**
   - What we know: The parameter is `measure_type_detailed_defense` in Python, mapping to `MeasureType=Advanced` in the NBA API.
   - What's unclear: Exact Python parameter naming may vary between nba_api versions.
   - Recommendation: Test the endpoint call early in development and verify the returned columns include `DEF_RATING` and `PACE`.

3. **Handling mid-season trades for DNP synthesis**
   - What we know: `CommonTeamRoster` returns end-of-season roster. Traded players appear on their final team.
   - What's unclear: Whether the NBA API provides transaction dates or roster-as-of-date snapshots.
   - Recommendation: Infer team membership from game log `MATCHUP` column. A player was "on" whichever team appears in their game logs for a given date range. Only synthesize DNP rows for games within that date range.

4. **Sample weighting decay rate (D-04 from user decisions)**
   - What we know: Recency decay is standard in sports ML. Common half-lives range from 15-30 games.
   - What's unclear: Optimal decay rate for NBA prop prediction specifically.
   - Recommendation: This is a Phase 3 (model training) concern. For Phase 1, ensure the `game_date` column is accurate and complete so Phase 3 can compute arbitrary decay weights. No data pipeline changes needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All pipeline code | ✓ | 3.14.0 (system) / 3.11 (Docker) | Docker uses 3.11-slim — compatible |
| SQLite | Data storage | ✓ | 3.43.2 | — |
| pip | Package installation | ✓ | 25.2 | — |
| Docker | Container runtime | ✓ (Dockerfile exists) | Unknown | Run pipeline locally without Docker |
| nba_api | NBA data source | ✓ (via pip) | 1.11.4 | — |

**Note:** Python 3.14.0 is installed system-wide but the Docker image uses `python:3.11-slim`. Both are compatible with all recommended packages. nba_api 1.11.4 requires `numpy>=2.1.0` — verify compatibility with the Docker Python 3.11 image (numpy 2.1+ supports 3.11).

**Missing dependencies with no fallback:**
- None — all dependencies are available via pip

**Missing dependencies with fallback:**
- `requests-cache`, `tenacity`, `tqdm`, `pytest` — not yet installed; add to `requirements.txt`

## Sources

### Primary (HIGH confidence)
- nba_api 1.11.4 — [PyPI](https://pypi.org/project/nba_api/), [GitHub](https://github.com/swar/nba_api) — session injection, endpoints, SeasonAll parameter
- requests-cache 1.3.1 — [Official Docs](https://requests-cache.readthedocs.io/en/latest/user_guide/backends/sqlite.html) — SQLite backend, CachedSession configuration
- tenacity — [Official Docs](https://tenacity.readthedocs.io/en/stable/) — retry decorators, exponential backoff + jitter
- nba_api PR #486 — [GitHub](https://github.com/swar/nba_api/pull/486) — `NBAHTTP.set_session()` implementation
- Stack Overflow — [Multi-season extraction](https://stackoverflow.com/questions/74648245) — SeasonAll.all usage pattern
- nba_api endpoint docs — [LeagueGameFinder](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamefinder.md), [CommonTeamRoster](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/commonteamroster.md)

### Secondary (MEDIUM confidence)
- hoopR R documentation — [LeagueDashTeamStats](https://hoopr.sportsdataverse.org/reference/nba_leaguedashteamstats.html), [TeamEstimatedMetrics](https://hoopr.sportsdataverse.org/reference/nba_teamestimatedmetrics.html) — parameter names and returned columns (R bindings, may differ slightly from Python)
- nba_api GitHub issues — [#405](https://github.com/swar/nba_api/issues/405), [#176](https://github.com/swar/nba_api/issues/176) — rate limiting behavior, timeout patterns

### Tertiary (LOW confidence)
- `LeagueDashTeamStats` Python parameter name (`measure_type_detailed_defense` vs `measure_type`) — needs verification against nba_api source code during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via PyPI, session injection verified via merged PR
- Architecture: HIGH — dual-layer caching is well-established pattern; SQLite schema follows standard practices
- Pitfalls: HIGH — sourced from nba_api GitHub issues, V1 codebase concerns audit, and established sports ML literature
- DNP synthesis approach: MEDIUM — logic is sound but mid-season trade handling needs validation during implementation
- Team advanced stats endpoint: MEDIUM — exact Python parameter names need verification

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (30 days — nba_api is relatively stable)
