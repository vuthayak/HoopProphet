# Phase 2: Feature Engineering Pipeline - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform raw SQLite game data (from Phase 1) into a training-ready feature matrix with rolling stats, contextual features, and binary over/under targets for every tracked stat. Output as Parquet with strict temporal integrity (`.shift(1)` — game N's features only contain data through game N-1). This is the bridge between raw data and model training.

</domain>

<decisions>
## Implementation Decisions

### Stat Scope
- **D-01:** Default to all 16 stat columns for full rolling features (pts, reb, ast, stl, blk, fg3m, fgm, fga, ftm, fta, oreb, dreb, tov, pf, plus_minus, min), BUT researcher should investigate whether sports ML literature recommends trimming to a curated subset to avoid noise. Planner implements what research recommends.
- **D-02:** Researcher should investigate which derived combo stats (PRA, PA, PR, fantasy points, double-double flags, usage rate) improve model performance in sports betting ML and include the recommended ones.

### Binary Target Lines
- **D-03:** Generate multiple threshold lines per player per stat — not a single line. This covers the range of prop lines sportsbooks offer.
- **D-04:** Researcher should determine how sportsbooks typically set lines and design the threshold generation to match that (e.g., percentile-based, fixed increments around mean, or hybrid). The line derivation approach should be informed by research.

### DNP Handling
- **D-05:** Skip DNP (zero-minute) rows when computing rolling averages. "Last 5 games" means last 5 games the player actually played (min > 0). DNP rows remain in the database for availability tracking but are excluded from performance feature computation.

### Edge Case Handling
- **D-06:** Exclude players below a minimum games-per-season threshold from the feature matrix. Researcher should determine the optimal minimum based on sports ML literature (rough range: 5-20 games).

### Matchup History
- **D-07:** For matchup history features (FEAT-08), use last 2 seasons of matchup data only. Older matchups are less relevant due to roster turnover.

### Opponent Defense
- **D-08:** Researcher should investigate whether per-position defensive data is available from nba_api or if team-level DEF_RATING with a position proxy is sufficient for FEAT-03.

### Pipeline Trigger
- **D-09:** Feature computation is chained with data ingest — ingest automatically triggers feature engineering after data collection completes. Single pipeline command handles both.

### Claude's Discretion
- Feature matrix format (wide vs long) — choose what works best with LightGBM binary classification
- Season-level aggregate features (season avg, games played, season std dev) — include if researcher finds them valuable
- File structure and module organization within `server/pipeline/`
- Parquet compression and partitioning strategy
- Feature naming conventions
- Logging and progress reporting during feature computation
- Handling of the first few games of a season where rolling windows are incomplete (NaN vs partial)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 Output (data source)
- `server/pipeline/db/schema.py` — SQLite table definitions: player_game_logs (16 stat columns + is_dnp), team_stats (def_rating, off_rating, net_rating, pace), team_rosters, team_schedules
- `server/pipeline/db/queries.py` — Existing query patterns for reading from SQLite
- `server/pipeline/db/connection.py` — Database connection management (WAL mode)

### Pipeline Architecture
- `.planning/research/ARCHITECTURE.md` — Offline pipeline architecture, feature engineering component spec
- `.planning/research/PITFALLS.md` — Temporal data leakage pitfall (#3), random train/test splits (#4), concept drift (#6)
- `.planning/research/STACK.md` — Parquet file strategy, pandas/numpy for feature engineering

### Model Requirements (downstream consumer)
- `.planning/REQUIREMENTS.md` — FEAT-01 through FEAT-10 specifications, MODL-01 (unified LightGBM classifier)
- `.planning/PROJECT.md` — Key decisions: binary classification framing, unified model across all players/props

### Existing Code
- `server/pipeline/ingest.py` — CLI orchestrator pattern to extend with feature computation chaining
- `server/pipeline/processors/dnp_synthesis.py` — DNP synthesis patterns, already handles roster × schedule cross-reference

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/pipeline/db/connection.py`: `get_connection()` for SQLite access with WAL mode — reuse for reading game data
- `server/pipeline/db/queries.py`: Parameterized SQL patterns — extend with feature-oriented read queries
- `server/pipeline/ingest.py`: CLI with argparse, `--full`/`--refresh` modes — extend to chain feature computation
- `server/pipeline/processors/` directory: Established location for data transformation modules

### Established Patterns
- Pipeline uses `server/pipeline/` package structure with `collectors/`, `processors/`, `db/` subpackages
- pandas DataFrames are the standard data manipulation tool throughout the pipeline
- SQLite for structured storage, with `INSERT OR IGNORE` dedup pattern
- `tqdm` progress bars for long-running operations
- `logging` module for structured logging (replacing V1's print statements)

### Integration Points
- Feature pipeline reads from `player_game_logs`, `team_stats`, `team_rosters`, `team_schedules` SQLite tables
- Feature pipeline writes Parquet file(s) consumed by Phase 3 (Model Training)
- Ingest CLI (`server/pipeline/ingest.py`) is the entry point to chain feature computation
- Tests in `server/tests/` — extend with feature engineering tests

</code_context>

<specifics>
## Specific Ideas

- User concerned that including all 16 stats may introduce noise/hallucination into the model — researcher should validate which stats contribute meaningful signal
- User wants target lines that mirror how sportsbooks set props — not arbitrary thresholds
- User emphasized recent performance matters most for bettors (from Phase 1 discussion) — rolling windows align with this, and recency decay (Phase 3) further reinforces it
- Matchup history limited to 2 seasons because rosters change — older matchups reflect different teams

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-feature-engineering-pipeline*
*Context gathered: 2026-03-23*
