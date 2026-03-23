# Phase 1: Data Pipeline & Caching - Context

**Gathered:** 2025-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a multi-season NBA data collection and caching layer. System collects game logs, team stats, and player data from NBA API, stores in SQLite, handles rate limits with retry logic, supports resumable fetching, and synthesizes zero-minute rows for DNP games. This is the data foundation that all downstream phases depend on.

</domain>

<decisions>
## Implementation Decisions

### Historical Depth
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Pipeline
- `.planning/research/STACK.md` — SQLite + Parquet caching strategy, nba_api rate limiting guidance
- `.planning/research/ARCHITECTURE.md` — Data Fetcher component spec, offline pipeline flow
- `.planning/research/PITFALLS.md` — NBA API rate limiting pitfall (#5), survivor bias pitfall (#2), concept drift (#6)

### Existing Code
- `server/ml/dataset.py` — V1 data fetching patterns (build_dataset, get_team_games, get_player_gamelog, player_inactive)
- `server/ml/prop_line.py` — V1 player ID resolution and career stats fetching
- `.planning/codebase/ARCHITECTURE.md` — Current data flow and NBA API integration patterns
- `.planning/codebase/CONCERNS.md` — NBA API rate limiting concerns, time.sleep(1) pattern, performance bottlenecks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/ml/dataset.py` `get_player_id()`: Player name → ID resolution (exists in two copies — consolidate)
- `server/ml/dataset.py` `get_season()`: Season string calculation from current date
- `server/ml/dataset.py` `get_team_games()`: Team game log fetching pattern
- `server/ml/dataset.py` `get_player_gamelog()`: Player game log fetching with multi-season support
- `server/ml/dataset.py` `player_inactive()`: Box score checking for inactive players (rate-limited with sleep(1))
- `nba_api` endpoint imports: `playergamelog`, `teamgamelog`, `boxscoresummaryv2`, `commonplayerinfo`, `playercareerstats`

### Established Patterns
- V1 uses `nba_api.stats.static.players.get_players()` for player lists and `nba_api.stats.static.teams.get_teams()` for team lists
- V1 handles multi-season data by checking if current season has <20 games, then falling back to previous season
- V1 uses `pd.DataFrame` operations throughout — pandas is the data manipulation standard

### Integration Points
- New SQLite cache replaces direct NBA API calls in `server/app.py` endpoints
- Feature engineering (Phase 2) will read from SQLite cache, not live API
- Data fetcher outputs must include: game logs, team stats (defensive ratings, pace), player metadata, and DNP-synthesized rows

</code_context>

<specifics>
## Specific Ideas

- User noted that bettors rely on recent performance, not deep history — sample weighting with recency decay addresses this while keeping historical depth for pattern learning
- All 450+ active players included for completeness (search bar covers everyone), even though bettors primarily care about starters and high-usage players
- Researcher should look into optimal sample weight decay rates for sports prediction models

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-pipeline-caching*
*Context gathered: 2025-03-22*
