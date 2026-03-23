# Phase 2: Feature Engineering Pipeline - Research

**Researched:** 2026-03-23
**Domain:** Sports ML feature engineering — NBA player prop prediction
**Confidence:** HIGH

## Summary

Phase 2 transforms raw SQLite game data from Phase 1 into a training-ready feature matrix for LightGBM binary classification. The core technical challenges are: (1) computing rolling statistics with strict temporal integrity (`.shift(1)` on every feature), (2) deriving meaningful contextual features (opponent defense, rest, pace, matchup history) from the existing database tables, and (3) generating multiple sportsbook-realistic threshold lines per player per stat for the binary over/under target.

The feature pipeline reads from `player_game_logs`, `team_stats`, `team_rosters`, and `team_schedules` SQLite tables (Phase 1 output) and writes a single Parquet file in "long" format — one row per (player, game, stat_type, line_value) — consumed by Phase 3 model training. Pandas `groupby().rolling().shift(1)` is the standard pattern for temporal-safe rolling features. The 16 raw stat columns should be kept (all provide signal in a unified model), supplemented with 3-4 derived combo stats (PRA, PA, PR) and rolling standard deviations for consistency measurement.

**Primary recommendation:** Use long-format feature matrix (one row per player×game×stat×line), compute rolling features with `groupby('player_id').rolling(window).mean().shift(1)` on DNP-excluded data, generate threshold lines at the player's recent median ± half-point increments, and write Parquet with snappy compression.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Default to all 16 stat columns for full rolling features (pts, reb, ast, stl, blk, fg3m, fgm, fga, ftm, fta, oreb, dreb, tov, pf, plus_minus, min), BUT researcher should investigate whether sports ML literature recommends trimming to a curated subset to avoid noise. Planner implements what research recommends.
- **D-02:** Researcher should investigate which derived combo stats (PRA, PA, PR, fantasy points, double-double flags, usage rate) improve model performance in sports betting ML and include the recommended ones.
- **D-03:** Generate multiple threshold lines per player per stat — not a single line. This covers the range of prop lines sportsbooks offer.
- **D-04:** Researcher should determine how sportsbooks typically set lines and design the threshold generation to match that (e.g., percentile-based, fixed increments around mean, or hybrid). The line derivation approach should be informed by research.
- **D-05:** Skip DNP (zero-minute) rows when computing rolling averages. "Last 5 games" means last 5 games the player actually played (min > 0). DNP rows remain in the database for availability tracking but are excluded from performance feature computation.
- **D-06:** Exclude players below a minimum games-per-season threshold from the feature matrix. Researcher should determine the optimal minimum based on sports ML literature (rough range: 5-20 games).
- **D-07:** For matchup history features (FEAT-08), use last 2 seasons of matchup data only. Older matchups are less relevant due to roster turnover.
- **D-08:** Researcher should investigate whether per-position defensive data is available from nba_api or if team-level DEF_RATING with a position proxy is sufficient for FEAT-03.
- **D-09:** Feature computation is chained with data ingest — ingest automatically triggers feature engineering after data collection completes. Single pipeline command handles both.

### Claude's Discretion
- Feature matrix format (wide vs long) — choose what works best with LightGBM binary classification
- Season-level aggregate features (season avg, games played, season std dev) — include if researcher finds them valuable
- File structure and module organization within `server/pipeline/`
- Parquet compression and partitioning strategy
- Feature naming conventions
- Logging and progress reporting during feature computation
- Handling of the first few games of a season where rolling windows are incomplete (NaN vs partial)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FEAT-01 | Rolling averages per stat across L5, L10, L20 game windows | Standard pandas `groupby().rolling(window).mean().shift(1)` pattern; DNP-excluded via `min > 0` filter |
| FEAT-02 | Rolling standard deviation per stat (consistency metric) | Same rolling pattern with `.std()` instead of `.mean()`; critical for identifying volatile vs consistent performers |
| FEAT-03 | Opponent defensive rating vs player position | nba_api `LeagueDashTeamStats` supports `player_position_abbreviation_nullable` for G/F/C; team_stats table has season-level DEF_RATING; hybrid approach recommended |
| FEAT-04 | Rest days and back-to-back game flags | Computed from `game_date` diff within player's game log; back-to-back = rest_days == 1 |
| FEAT-05 | Home/away indicator | Parsed from `matchup` column: contains "vs." = home (1), contains "@" = away (0) |
| FEAT-06 | Team pace and opponent pace features | Read from `team_stats` table (pace column); opponent team parsed from matchup |
| FEAT-07 | Minutes trend features | Rolling average of `min` column across L5 window; already part of rolling feature computation |
| FEAT-08 | Historical matchup stats (player avg vs specific opponent) | Query player_game_logs filtered by opponent team within last 2 seasons; compute mean per stat |
| FEAT-09 | Temporal guard — `.shift(1)` on all features | Every rolling/cumulative feature shifted by 1 within player group; verified by automated leakage test |
| FEAT-10 | Parquet output with binary target column | Long-format Parquet: one row per (player, game, stat_type, line_value) with `hit` binary column |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.2.3 | Rolling windows, groupby aggregations, feature matrix construction | Already installed; `groupby().rolling()` is the standard pattern for player-specific windowed stats |
| numpy | 2.1.3 | Numerical operations, NaN handling, array computation | Already installed; transitive dependency of pandas |
| pyarrow | 19.0.0 | Parquet I/O engine for pandas | Already installed; enables `.to_parquet()` and `.read_parquet()` with snappy compression |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tqdm | 4.67.1 | Progress bars for long feature computation | Already installed; use during per-player feature loops |
| sqlite3 | stdlib | Read Phase 1 data from SQLite | Already used in Phase 1; no additional install needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas rolling | polars lazy eval | Polars is faster for large datasets but the team already uses pandas throughout; ~500K rows is well within pandas capacity |
| pyarrow Parquet | DuckDB feature store | DuckDB supports SQL queries on Parquet but adds complexity; Parquet files are sufficient for single-writer pipeline |
| Manual rolling loops | featuretools | Auto-feature-engineering library; overkill for well-defined domain features, and sports features require custom logic |

**Installation:**
```bash
# No new dependencies needed — all already available
# pyarrow must be added to server/requirements.txt since it's used but not listed
pyarrow>=19.0.0
```

## Architecture Patterns

### Recommended Project Structure
```
server/pipeline/
├── __init__.py              # SEASONS, DATA_DIR, DB_PATH, CACHE_PATH (existing)
├── ingest.py                # Extend with --features flag to chain feature engineering
├── features.py              # NEW: Main orchestrator for feature pipeline
├── db/
│   ├── connection.py        # Reuse get_connection() (existing)
│   ├── queries.py           # Extend with feature-oriented read queries
│   └── schema.py            # Existing — no changes needed
├── processors/
│   ├── dnp_synthesis.py     # Existing
│   ├── rolling_features.py  # NEW: Rolling avg/std computation with .shift(1)
│   ├── contextual_features.py  # NEW: Rest days, home/away, pace, opponent defense
│   ├── matchup_features.py  # NEW: Historical matchup stats
│   └── target_generator.py  # NEW: Binary over/under target with multi-line thresholds
├── nba_client.py            # Existing
└── collectors/              # Existing Phase 1 collectors
```

### Pattern 1: Temporal-Safe Rolling Features
**What:** Every rolling statistic uses `groupby('player_id').rolling(window).agg().shift(1)` to ensure game N's features contain only data through game N-1.
**When to use:** Every feature derived from historical game data.
**Example:**
```python
# Source: pandas docs + sports ML best practice
# Filter out DNP rows for performance features
played = df[df['is_dnp'] == 0].copy()
played = played.sort_values(['player_id', 'game_date'])

for window in [5, 10, 20]:
    for stat in STAT_COLS:
        col_name = f'{stat}_avg_L{window}'
        played[col_name] = (
            played.groupby('player_id')[stat]
            .rolling(window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
            .groupby(played['player_id'])
            .shift(1)
        )
```

### Pattern 2: Long-Format Feature Matrix for Unified Model
**What:** One row per (player_id, game_id, stat_type, line_value) with a binary `hit` target column. This format lets a single LightGBM model learn across all stat types simultaneously.
**When to use:** For binary classification with a unified model across stat types.
**Why:** LightGBM handles `stat_type` as a categorical feature, learning that different stats have different distributions. Wide format (one row per game with all stats as separate targets) would require separate models per stat.
**Example:**
```python
# Each game generates multiple rows — one per (stat_type, line_value)
# stat_type encoded as integer: 0=pts, 1=reb, 2=ast, ...
{
    "player_id": 203999,
    "game_date": "2023-11-01",
    "stat_type": 0,           # pts
    "line_value": 24.5,
    "rolling_5_avg_pts": 26.2,
    "rolling_10_avg_pts": 25.1,
    "rolling_5_std_pts": 4.3,
    "opp_def_rating": 112.3,
    "opp_def_vs_position": 108.7,
    "rest_days": 2,
    "is_back_to_back": 0,
    "is_home": 1,
    "team_pace": 100.2,
    "opp_pace": 98.5,
    "min_avg_L5": 34.8,
    "matchup_avg": 27.5,
    "season_avg": 25.8,
    "games_played_season": 15,
    "hit": 1                  # actual pts (28) > line_value (24.5)
}
```

### Pattern 3: Hybrid Line Generation (Median-Based + Fixed Increments)
**What:** Generate threshold lines centered on the player's recent median (not mean), with half-point increments above and below. This mirrors how sportsbooks set lines.
**When to use:** For FEAT-10 binary target generation.
**Why:** Sportsbooks set lines at the median (50/50 split point), not the mean. The mean gets inflated by outlier games (right-skewed distributions). Using median-centered lines with ±0.5 increments produces training data that matches the lines bettors actually encounter.
**Example:**
```python
# For each player × stat, compute recent median from L20 games
# Generate lines at: median - 2.5, median - 1.5, median - 0.5,
#                    median + 0.5, median + 1.5, median + 2.5
# Round to nearest .5 (sportsbook convention)
import numpy as np

def generate_lines(recent_values: pd.Series, n_lines: int = 5) -> list[float]:
    median = recent_values.median()
    base = round(median * 2) / 2  # Round to nearest 0.5
    offsets = np.arange(-(n_lines // 2), (n_lines // 2) + 1) * 1.0
    lines = [base + offset for offset in offsets]
    return [max(0.5, line) for line in lines]  # Floor at 0.5
```

### Anti-Patterns to Avoid
- **Computing rolling stats without `.shift(1)`:** Creates temporal leakage — game N's features include game N's outcome. Back-test accuracy will be artificially high (>70%) but live performance will be coin-flip.
- **Using mean instead of median for line generation:** Mean is inflated by outlier games; sportsbooks use median as the 50/50 split point. Lines based on mean will be systematically too high.
- **Including DNP rows in rolling averages:** A player's "last 5 games" average should exclude zero-minute rows. Including them drags averages toward zero unrealistically.
- **Using season-end team stats for mid-season games:** Opponent DEF_RATING must be computed as-of game date, not end-of-season aggregates. Phase 1 stores season-level stats; use them as a reasonable proxy (acknowledged MEDIUM confidence — see Open Questions).
- **One-hot encoding stat_type:** LightGBM handles categorical features natively (8x faster than one-hot). Pass `stat_type` as categorical integer, not one-hot columns.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling window aggregations | Custom loop over game history | `pandas.groupby().rolling()` | Handles edge cases (NaN, min_periods, group boundaries); vectorized and fast |
| Parquet I/O | CSV or custom binary format | `pandas.to_parquet()` with pyarrow | Preserves dtypes, columnar compression, ~10x faster reads than CSV |
| Date arithmetic (rest days) | Manual string parsing | `pd.to_datetime()` + `.diff()` | Handles timezones, leap years, edge cases automatically |
| Opponent team extraction from matchup | Regex parsing | Simple string split on "vs." / "@" | Matchup format is consistent: "TEA vs. OPP" or "TEA @ OPP" |

**Key insight:** The feature engineering domain is well-served by pandas built-in operations. No specialized sports ML library exists that handles NBA prop features better than pandas + domain knowledge. The competitive advantage is in feature design, not tooling.

## Research Findings

### D-01: Stat Column Selection — Keep All 16

**Recommendation: Keep all 16 stat columns for rolling features.** [HIGH confidence]

**Rationale:** In a unified model trained across all players and all stat types, each stat column serves dual purpose:
1. **As a target stat:** When predicting pts over/under, the rolling average of pts is the primary predictor.
2. **As contextual signal:** When predicting pts, rolling ast and fgm provide usage context. When predicting reb, oreb/dreb splits provide composition signal.

LightGBM's tree-based architecture naturally handles irrelevant features — it simply won't split on features with no predictive value. The risk of "noise" from including all 16 is minimal because:
- Tree models are robust to irrelevant features (unlike linear models).
- With 100K+ training rows, the model has sufficient samples to distinguish signal from noise.
- Feature importance analysis (SHAP in Phase 3) will identify which features actually contribute.

**Stats to include in rolling features (all 16):** pts, reb, ast, stl, blk, fg3m, fgm, fga, ftm, fta, oreb, dreb, tov, pf, plus_minus, min

However, to manage feature matrix width, compute rolling features for all 16 stats but only for the **L5 and L10 windows** for less commonly bet stats (oreb, dreb, fga, fta, pf, tov, fgm, ftm). Use all three windows (L5, L10, L20) for the primary prop stats: pts, reb, ast, stl, blk, fg3m, plus_minus, min.

### D-02: Derived Combo Stats — Include PRA, PA, PR

**Recommendation: Include PRA, PA, and PR as derived stats. Skip fantasy points and double-double flags.** [HIGH confidence]

**Rationale:**
- **PRA (Points + Rebounds + Assists):** The most commonly offered combo prop on sportsbooks. Sportsbooks specifically offer PRA lines, so the model should learn to predict PRA over/under directly.
- **PA (Points + Assists):** Second most common combo prop. Captures scoring playmakers (guards).
- **PR (Points + Rebounds):** Third most common combo prop. Captures scoring bigs (forwards/centers).
- **Fantasy points:** Not offered as a prop line by mainstream sportsbooks (DraftKings/FanDuel offer them for DFS but not as betting props). Skip.
- **Double-double flags:** Binary and extremely sparse — most players never get double-doubles. The model would have insufficient positive samples per player. Skip.
- **Usage rate:** Requires play-by-play data not available in our game log tables. Skip for Phase 2; consider for future enhancement.

Compute rolling averages and standard deviations for PRA, PA, PR the same way as individual stats. Generate threshold lines for them as additional stat types.

### D-04: Line Generation — Median-Centered with Half-Point Increments

**Recommendation: Generate 5 threshold lines per player per stat, centered on the L20 median with ±0.5 unit increments, rounded to nearest 0.5.** [HIGH confidence]

**How sportsbooks set lines (from research):**
- Lines are set at the **median** (50/50 split point), not the mean. The mean gets inflated by outlier performances.
- Lines are typically in **0.5 increments** (e.g., 24.5, 25.5, not 24.3).
- Sportsbooks then adjust for matchup context, but the starting point is the player's recent median.
- Different sportsbooks may offer slightly different lines, so generating a range around the median captures the variance.

**Implementation:**
1. Compute L20 median for each player × stat (excluding DNPs, with `.shift(1)`)
2. Round median to nearest 0.5 → this is the center line
3. Generate 5 lines: center - 2.0, center - 1.0, center, center + 1.0, center + 2.0
4. Floor all lines at 0.5 (no zero or negative lines)
5. For high-volume stats (pts), consider wider spread: ±1.5 increments for 5 lines

This produces 5 training rows per player per game per stat type — a good balance between coverage and dataset size. With ~450 players × ~80 games × 10 stat types × 5 lines = ~18M rows. This is large but manageable with Parquet compression. **Alternative:** reduce to 3 lines per stat (center - 1.0, center, center + 1.0) to keep ~11M rows. Start with 3 lines and scale up if model needs more variety.

**Updated recommendation:** Use **3 lines per stat** (center - 1.0, center, center + 1.0) to keep feature matrix at ~11M rows. This still covers the typical sportsbook spread around the median.

### D-06: Minimum Games Threshold — 10 Games Per Season

**Recommendation: Require at least 10 games played (min > 0) per season for inclusion in the feature matrix.** [MEDIUM confidence]

**Rationale:**
- **Below 5 games:** Rolling L5 averages are based on fewer than 5 data points, meaning every feature is computed from incomplete windows. Not enough signal for the model.
- **10 games (recommended):** Provides a full L10 rolling window, ensures the player has meaningful sample size, and excludes two-way contract players / end-of-bench guys who play <10 games.
- **20 games:** Too aggressive — would exclude legitimate players who missed time due to injury mid-season but are still valuable prediction targets when active.
- **Academic precedent:** NBA analytics papers typically use 20+ minutes per game filters rather than game count filters, but since we're doing per-game binary classification (not season-level), a minimum game count is more appropriate.

The 10-game threshold is applied **per season** — a player who plays 8 games in 2021-22 but 70 in 2022-23 only has their 2022-23 data included.

### D-08: Opponent Defense vs Position — Hybrid Approach

**Recommendation: Use team-level DEF_RATING from team_stats table as primary, with position-mapped proxy. Optionally collect per-position data in Phase 2 as enhancement.** [MEDIUM confidence]

**Findings:**
- **nba_api DOES support per-position defensive data** via `LeagueDashTeamStats` with `measure_type_detailed_defense='Opponent'` and `player_position_abbreviation_nullable='G'|'F'|'C'`. This returns how many points/rebounds/assists teams allow against guards, forwards, and centers specifically.
- **However:** This requires additional API calls during data collection (not feature engineering). Phase 1 already collected `team_stats` with season-level DEF_RATING. Per-position data is not in the database.
- **Practical approach for Phase 2:** Use team-level `def_rating` from `team_stats` table joined by opponent team ID + season. Map the player's `position` field (from `players` table) as a separate categorical feature. The model can learn "center vs. good defense" interactions through tree splits.
- **Enhancement path:** Add per-position defensive data collection to the ingest pipeline (a new collector that calls `LeagueDashTeamStats` filtered by position). This would require 3 API calls per team per season (G, F, C) × 30 teams × 5 seasons = 450 additional API calls — feasible but adds pipeline complexity.

**For Phase 2:** Use team-level DEF_RATING + player position categorical. This is sufficient for the initial model and avoids scope creep into data collection.

### Season-Level Aggregate Features — Include

**Recommendation: Include season-to-date averages and games played count as features.** [HIGH confidence]

**Rationale:** Season-level aggregates provide baseline context that rolling windows don't capture:
- `season_avg_{stat}`: The player's season-to-date average (expanding mean with `.shift(1)`)
- `games_played_season`: How many games the player has played this season (expanding count with `.shift(1)`)
- `season_std_{stat}`: Season-to-date standard deviation for the primary stats

These help the model distinguish "hot streak above season norm" from "consistently high performer" — both have high L5 averages but different season averages.

### Feature Matrix Format — Long Format

**Recommendation: Long format — one row per (player_id, game_id, stat_type, line_value).** [HIGH confidence]

**Why long format for LightGBM binary classification:**
- The model's task is binary: "does stat X exceed line Y?" This is naturally one prediction per row.
- `stat_type` becomes a categorical feature that LightGBM handles natively (8x faster than one-hot encoding).
- Long format enables a truly unified model — it learns cross-stat patterns (e.g., "when pts rolling avg is high, PRA is likely over too").
- Wide format would require either: (a) separate models per stat type (loses cross-stat learning), or (b) multi-output classification (not supported by LightGBM binary objective).

### Handling Incomplete Rolling Windows — Use min_periods=1, NaN for L20 Only

**Recommendation:** For games early in the season where fewer than `window` games exist:
- **L5, L10:** Use `min_periods=1` — compute average from available games (e.g., first 3 games → average of 2 prior games after shift). This provides useful signal even with partial windows.
- **L20:** Use `min_periods=10` — require at least 10 prior games before computing L20 average. Below that, the L20 feature is NaN. LightGBM handles NaN natively (routes to the optimal child node during splitting).
- **Season averages:** Use expanding window with `min_periods=1` — always available after 1 game played.

### Parquet Compression — Snappy (Default)

**Recommendation: Use snappy compression (pandas default).** [HIGH confidence]

**Rationale:** Snappy is the best balance for this use case:
- Read speed is priority (model training reads the full file repeatedly).
- Compression ratio is secondary (dataset is ~1-3 GB uncompressed, ~200-500 MB with snappy).
- Snappy is the pandas/pyarrow default — zero configuration needed.
- Zstd offers better compression but slower reads; not worth the tradeoff at this scale.

**No partitioning needed.** The feature matrix is read in full for training. Partition-by-season would only help if we queried subsets, but LightGBM loads the full dataset.

### Feature Naming Convention

**Recommendation:** `{stat}_{agg}_{window}` pattern.

Examples:
- `pts_avg_L5` — Points rolling 5-game average
- `reb_std_L10` — Rebounds rolling 10-game standard deviation
- `pra_avg_L5` — PRA combo rolling 5-game average
- `pts_season_avg` — Points season-to-date average
- `opp_def_rating` — Opponent team defensive rating
- `opp_pace` — Opponent team pace
- `team_pace` — Player's team pace
- `rest_days` — Days since last game
- `is_b2b` — Back-to-back flag (0/1)
- `is_home` — Home game flag (0/1)
- `matchup_avg_{stat}` — Historical average vs this opponent
- `min_avg_L5` — Minutes rolling 5-game average
- `games_played_season` — Season game count

### Pipeline Chaining

**Recommendation:** Extend `ingest.py` with a `--features` flag that triggers feature engineering after data collection. Also support `--features-only` for running feature computation without re-ingesting.

```python
# In ingest.py main():
parser.add_argument("--features", action="store_true",
    help="Run feature engineering after data collection")
parser.add_argument("--features-only", action="store_true",
    help="Run feature engineering only (skip data collection)")
```

## Common Pitfalls

### Pitfall 1: Temporal Leakage via Missing `.shift(1)`
**What goes wrong:** Rolling averages include current game's stats in the feature for that game. Model appears 75%+ accurate in back-test but fails in production.
**Why it happens:** Pandas `rolling().mean()` includes the current row by default. Without `.shift(1)`, game N's "last 5 games avg" includes game N itself.
**How to avoid:** Apply `.shift(1)` after every rolling/expanding computation, within the player's group. Add automated leakage test: if back-test accuracy >65% on binary props, suspect leakage.
**Warning signs:** Suspiciously high back-test accuracy; feature importance shows rolling averages dominating unrealistically.

### Pitfall 2: Including DNP Rows in Rolling Averages
**What goes wrong:** A player misses 3 games (DNP), and their "L5 average" includes three 0-point games, making the model predict they'll underperform dramatically in their return game.
**Why it happens:** DNP rows exist in `player_game_logs` (from Phase 1 synthesis) with all stats = 0. If not filtered, they pollute rolling computations.
**How to avoid:** Filter `is_dnp == 0` before computing any performance rolling features. DNP rows stay in the database for availability tracking (rest days computation still uses them for date gaps).
**Warning signs:** Unexpected dips in rolling averages after players return from absence.

### Pitfall 3: Opponent Team Extraction Fails for Trade Scenarios
**What goes wrong:** Matchup column shows "DEN vs. LAL" but player was traded mid-season. The player's team abbreviation changed, so opponent extraction logic breaks.
**Why it happens:** Matchup format encodes the player's team at game time, which changes after trades.
**How to avoid:** Parse opponent from matchup based on position — if "vs." appears, opponent is after "vs."; if "@" appears, opponent is after "@". The player's team is always first. Extract both.
**Warning signs:** NULL opponent features for recently traded players.

### Pitfall 4: Feature Matrix Size Explosion
**What goes wrong:** With 450 players × 80 games × 13 stat types × 5 lines = 23.4M rows. Feature matrix becomes unwieldy, training slows down.
**Why it happens:** Long format with many stat types and many threshold lines multiplies row count rapidly.
**How to avoid:** Start with 3 lines per stat (not 5). Use only the 10 primary stat types for threshold lines (pts, reb, ast, stl, blk, fg3m, PRA, PA, PR, min). This yields ~450 × 80 × 10 × 3 = ~10.8M rows — manageable with LightGBM (handles 10M+ rows efficiently with histogram binning).
**Warning signs:** Feature computation takes >30 minutes; Parquet file exceeds 2 GB.

### Pitfall 5: Season-Level Team Stats Used for All Games
**What goes wrong:** The `team_stats` table stores one row per team per season with season-end DEF_RATING. Using the end-of-season value for an October game introduces mild forward-looking bias.
**Why it happens:** Phase 1 collected season-level aggregates, not game-by-game evolving stats.
**How to avoid:** Acknowledge this as a known approximation. Season-level defensive ratings are relatively stable (correlation >0.85 between mid-season and end-of-season values). For Phase 2, this is an acceptable tradeoff. Flag for improvement in a future phase (game-by-game rolling team stats).
**Warning signs:** None immediately — this is a known limitation, not a bug.

## Code Examples

Verified patterns from official pandas documentation and sports ML practice:

### Rolling Features with Temporal Guard
```python
# Source: pandas.pydata.org/docs + sports ML best practice
import pandas as pd

STAT_COLS = ['pts', 'reb', 'ast', 'stl', 'blk', 'fg3m', 'fgm', 'fga',
             'ftm', 'fta', 'oreb', 'dreb', 'tov', 'pf', 'plus_minus', 'min']
PRIMARY_STATS = ['pts', 'reb', 'ast', 'stl', 'blk', 'fg3m', 'plus_minus', 'min']
COMBO_STATS = {'pra': ['pts', 'reb', 'ast'], 'pa': ['pts', 'ast'], 'pr': ['pts', 'reb']}
WINDOWS = {'primary': [5, 10, 20], 'secondary': [5, 10]}

def compute_rolling_features(played: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling avg and std with .shift(1) temporal guard."""
    played = played.sort_values(['player_id', 'game_date']).copy()

    for stat in STAT_COLS:
        windows = WINDOWS['primary'] if stat in PRIMARY_STATS else WINDOWS['secondary']
        for w in windows:
            played[f'{stat}_avg_L{w}'] = (
                played.groupby('player_id')[stat]
                .rolling(w, min_periods=1).mean()
                .reset_index(level=0, drop=True)
            )
            played[f'{stat}_std_L{w}'] = (
                played.groupby('player_id')[stat]
                .rolling(w, min_periods=1).std()
                .reset_index(level=0, drop=True)
            )

    # Shift ALL rolling features by 1 within each player group
    rolling_cols = [c for c in played.columns if '_avg_L' in c or '_std_L' in c]
    played[rolling_cols] = played.groupby('player_id')[rolling_cols].shift(1)

    return played
```

### Opponent Feature Extraction
```python
# Source: Phase 1 schema + matchup column format
def extract_opponent_team(matchup: str) -> str:
    """Extract opponent abbreviation from matchup string."""
    if ' vs. ' in matchup:
        return matchup.split(' vs. ')[1].strip()
    elif ' @ ' in matchup:
        return matchup.split(' @ ')[1].strip()
    return None

def add_opponent_features(df: pd.DataFrame, team_stats: pd.DataFrame,
                          teams: pd.DataFrame) -> pd.DataFrame:
    """Join opponent DEF_RATING and pace from team_stats table."""
    df['opp_abbr'] = df['matchup'].apply(extract_opponent_team)
    abbr_to_id = dict(zip(teams['abbreviation'], teams['team_id']))
    df['opp_team_id'] = df['opp_abbr'].map(abbr_to_id)

    opp_stats = team_stats[['team_id', 'season', 'def_rating', 'pace']].rename(
        columns={'team_id': 'opp_team_id', 'def_rating': 'opp_def_rating', 'pace': 'opp_pace'}
    )
    df = df.merge(opp_stats, on=['opp_team_id', 'season'], how='left')
    return df
```

### Binary Target Generation
```python
# Source: sportsbook methodology research
def generate_target_rows(player_games: pd.DataFrame, stat: str,
                         n_lines: int = 3) -> pd.DataFrame:
    """Generate binary over/under rows for multiple threshold lines."""
    rows = []
    for player_id, group in player_games.groupby('player_id'):
        group = group.sort_values('game_date')
        # L20 median with .shift(1) for line derivation
        group['_median'] = (
            group[stat].rolling(20, min_periods=5).median().shift(1)
        )
        for _, game in group.iterrows():
            if pd.isna(game['_median']):
                continue
            base = round(game['_median'] * 2) / 2  # Round to nearest 0.5
            for offset in range(-1, 2):  # -1, 0, +1
                line = max(0.5, base + offset)
                rows.append({
                    **game.to_dict(),
                    'stat_type': stat,
                    'line_value': line,
                    'hit': int(game[stat] > line),
                })
    return pd.DataFrame(rows)
```

### Rest Days and Back-to-Back Detection
```python
# Source: pandas date arithmetic
def compute_rest_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rest days and back-to-back flag from game dates."""
    df = df.sort_values(['player_id', 'game_date']).copy()
    df['game_date_dt'] = pd.to_datetime(df['game_date'])
    df['rest_days'] = (
        df.groupby('player_id')['game_date_dt']
        .diff()
        .dt.days
        .fillna(7)  # First game of season — assume rested
        .clip(upper=14)  # Cap at 14 (All-Star break / long rest)
    )
    df['is_b2b'] = (df['rest_days'] == 1).astype(int)
    return df
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Season averages as features | Rolling windows (L5, L10, L20) | ~2022 | Captures form/trend; 5-10% accuracy improvement |
| Mean-based prop lines | Median-based lines | Ongoing | Better reflects sportsbook methodology; reduces right-skew inflation |
| Per-player models | Unified model across all players | ~2023 | 100x more training data; better generalization; one model to maintain |
| Random k-fold CV | Walk-forward temporal splits | ~2023 | Eliminates temporal leakage in evaluation; honest metrics |
| Linear regression for stat prediction | Binary classification for prop probability | ~2024 | Directly outputs what bettors need (probability); better calibration |

**Deprecated/outdated:**
- XGBoost for this use case: LightGBM is faster and handles categoricals natively. XGBoost still works but is not the optimal choice.
- Simple moving averages: Exponentially weighted moving averages (EWM) can be added in Phase 3 for recency decay, but simple rolling is standard for Phase 2.

## Open Questions

1. **Season-level vs game-level opponent defensive ratings**
   - What we know: Phase 1 stores season-level `def_rating` per team. This is a reasonable approximation.
   - What's unclear: Whether mid-season games have significantly different opponent strength than the season-end aggregate suggests.
   - Recommendation: Use season-level stats for Phase 2. If back-testing reveals opponent features have low importance, investigate game-level rolling team stats as a future enhancement.

2. **Optimal number of threshold lines per stat**
   - What we know: 3 lines (center ± 1.0) keeps matrix at ~11M rows. 5 lines gives more variety but ~18M rows.
   - What's unclear: Whether additional lines improve model generalization enough to justify the computational cost.
   - Recommendation: Start with 3 lines. Evaluate after Phase 3 training — if model struggles at extreme lines, expand to 5.

3. **Cross-season rolling windows**
   - What we know: Seasons are stored with `season` column. Rolling windows that span the off-season (last games of 2022-23 → first games of 2023-24) carry stale data.
   - What's unclear: Whether to reset rolling windows at season boundaries or let them span across seasons.
   - Recommendation: Allow cross-season rolling (don't reset). Rationale: the L5 and L10 windows will naturally age out old data quickly, and the model benefits from having features available in early-season games (otherwise first 5-20 games per season have all-NaN features).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | ✓ | 3.13.5 (anaconda) | — |
| pandas | Feature computation | ✓ | 2.2.3 | — |
| numpy | Numerical ops | ✓ | 2.1.3 | — |
| pyarrow | Parquet I/O | ✓ | 19.0.0 | — |
| pytest | Testing | ✓ | 8.3.4 | — |
| tqdm | Progress bars | ✓ | 4.67.1 | — |
| SQLite | Data source | ✓ | stdlib | — |
| server/data/hoopprophet.db | Phase 1 output | ✓ | 65KB (empty/small) | Run `--full` ingest first |

**Missing dependencies with no fallback:** None — all dependencies are available.

**Note:** `pyarrow` is installed in the environment but not listed in `server/requirements.txt`. Add it during Phase 2 implementation.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | None (uses defaults; tests in `server/tests/`) |
| Quick run command | `python -m pytest server/tests/test_features.py -x` |
| Full suite command | `python -m pytest server/tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FEAT-01 | Rolling averages L5/L10/L20 computed correctly | unit | `python -m pytest server/tests/test_features.py::test_rolling_averages -x` | ❌ Wave 0 |
| FEAT-02 | Rolling std dev computed correctly | unit | `python -m pytest server/tests/test_features.py::test_rolling_std -x` | ❌ Wave 0 |
| FEAT-03 | Opponent defensive rating joined correctly | unit | `python -m pytest server/tests/test_features.py::test_opponent_features -x` | ❌ Wave 0 |
| FEAT-04 | Rest days and B2B flags computed correctly | unit | `python -m pytest server/tests/test_features.py::test_rest_days -x` | ❌ Wave 0 |
| FEAT-05 | Home/away indicator from matchup string | unit | `python -m pytest server/tests/test_features.py::test_home_away -x` | ❌ Wave 0 |
| FEAT-06 | Team pace and opponent pace joined | unit | `python -m pytest server/tests/test_features.py::test_pace_features -x` | ❌ Wave 0 |
| FEAT-07 | Minutes trend (rolling avg of min) | unit | `python -m pytest server/tests/test_features.py::test_minutes_trend -x` | ❌ Wave 0 |
| FEAT-08 | Matchup history within 2-season window | unit | `python -m pytest server/tests/test_features.py::test_matchup_history -x` | ❌ Wave 0 |
| FEAT-09 | No temporal leakage — all features shifted | integration | `python -m pytest server/tests/test_features.py::test_no_leakage -x` | ❌ Wave 0 |
| FEAT-10 | Parquet output with binary hit column | integration | `python -m pytest server/tests/test_features.py::test_parquet_output -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest server/tests/test_features.py -x`
- **Per wave merge:** `python -m pytest server/tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `server/tests/test_features.py` — covers FEAT-01 through FEAT-10
- [ ] Extend `server/tests/conftest.py` — add fixtures for multi-game, multi-player, multi-season test data with known expected rolling values

## Sources

### Primary (HIGH confidence)
- pandas official docs — `groupby().rolling()`, `.shift()`, `.to_parquet()` API reference
- Phase 1 codebase — `server/pipeline/db/schema.py` (table definitions), `server/pipeline/db/queries.py` (query patterns), `server/pipeline/ingest.py` (CLI pattern)
- `.planning/research/PITFALLS.md` — Temporal leakage (#3), survivor bias (#2), concept drift (#6)
- `.planning/research/ARCHITECTURE.md` — Feature store Parquet pattern, data flow, binary classification framing
- `.planning/research/STACK.md` — pandas for feature engineering, pyarrow for Parquet

### Secondary (MEDIUM confidence)
- nba_api GitHub Issue #417 — Per-position defensive stats via `LeagueDashTeamStats` with `player_position_abbreviation_nullable`
- DumbMoneyPicks.ai — Sportsbooks set lines at median, not mean; right-skewed stat distributions
- Kingsley Onoh (dev.to) — Minutes prediction as gatekeeper, shifted rolling averages pattern
- Mitchell Dawkins prop predictor — Feature engineering approach: rolling windows, opponent ratings, pace
- Cardinal Media / Ball State Daily News — Sportsbook line-setting methodology: algorithms + expert judgment + market dynamics

### Tertiary (LOW confidence)
- Analytics Vidhya (2026) — General lag/rolling feature guide; not sports-specific but confirms patterns
- Stat Pick AI blog — Sharp bettors exploit sportsbook model gaps in context features

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and verified; patterns well-established
- Architecture: HIGH — long-format feature matrix + temporal-safe rolling is the consensus approach in sports ML
- Pitfalls: HIGH — extensively documented in Phase 1 planning research; temporal leakage is the #1 risk
- Line generation: MEDIUM — sportsbook methodology is proprietary; median-based approach is informed inference
- Opponent defense: MEDIUM — team-level DEF_RATING is a known approximation; per-position data is available but adds collection scope

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days — stable domain, no fast-moving dependencies)
