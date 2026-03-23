# Phase 2: Feature Engineering Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 02-feature-engineering-pipeline
**Areas discussed:** Tracked stats scope (expanded to cover target lines, DNP handling, combo stats, edge cases, matchup history, opponent defense, pipeline trigger, season features, output shape)

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Tracked stats scope | Which stats get rolling features? All 16 or curated subset? | ✓ |
| Binary target line definition | How "the line" for over/under is defined | |
| DNP games in rolling windows | Include or skip zero-minute rows in L5/L10/L20 | |
| Derived/combo features | PRA, fantasy points, double-double flags | |

**Note:** User selected only "stats scope" but follow-up questions naturally covered the other areas.

---

## Stat Scope — Which stats get full rolling features?

| Option | Description | Selected |
|--------|-------------|----------|
| Core betting props only (6 stats) | pts, reb, ast, stl, blk, fg3m | |
| Extended set (10 stats) | Core 6 + fgm, ftm, tov, oreb | |
| All 16 stat columns | Maximum flexibility | |
| Other | Different grouping | |

**User's choice:** Free text — "We can use all 16 stat columns, but if you think this will introduce model hallucination, then don't. Research what other sports ML models do (if possible) and determine the correct approach to this."
**Notes:** User open to all 16 but concerned about noise. Deferred to researcher to validate.

---

## Binary Target Line Definition

| Option | Description | Selected |
|--------|-------------|----------|
| Player's season average | Simple, reflects actual performance level | |
| Player's recent rolling average | L10/L20, dynamic but potential leakage risk | |
| Multiple lines per stat | Several thresholds covering sportsbook range | ✓ |
| Research this | Researcher determines best approach | |

**User's choice:** Multiple lines per stat

---

## Line Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Percentile-based (P25/P50/P75) | Adapts per player automatically | |
| Fixed 0.5 increments around mean | Uniform coverage | |
| Hybrid | Research-determined range with .5 increments | |
| Research this | Let researcher figure out how sportsbooks set lines | ✓ |

**User's choice:** Research this — let researcher determine sportsbook-aligned approach

---

## DNP Games in Rolling Windows

| Option | Description | Selected |
|--------|-------------|----------|
| Skip DNPs | L5 = last 5 games actually played | ✓ |
| Include DNPs as zeros | Captures availability risk, distorts stats | |
| You decide | Claude's discretion | |

**User's choice:** Skip DNPs

---

## Derived/Combo Stats

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include combo stats | PRA, PA, PR, fantasy points, double-double | |
| No, stick to base stats | Keep simple | |
| Research which combos matter | Researcher determines | ✓ |

**User's choice:** Research which combo stats matter

---

## Edge Cases — Minimum Games Threshold

| Option | Description | Selected |
|--------|-------------|----------|
| 5 games | Very lenient | |
| 10 games | Moderate | |
| 20 games | Stricter | |
| Research this | Researcher determines optimal minimum | ✓ |

**User's choice:** Research optimal minimum

---

## Output Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Wide format (1 row per player-game) | All features as columns | |
| Long format (1 row per player-game-stat) | Natural for multi-line targets | |
| You decide | Claude's discretion | ✓ |

**User's choice:** You decide

---

## Matchup History Depth

| Option | Description | Selected |
|--------|-------------|----------|
| All available history (5 seasons) | Maximum data | |
| Recent history only (2 seasons) | More relevant due to roster turnover | ✓ |
| You decide | Claude's discretion | |

**User's choice:** Recent history only (last 2 seasons)

---

## Opponent Defensive Rating vs Position

| Option | Description | Selected |
|--------|-------------|----------|
| Team-level DEF_RATING only | Simple, already in SQLite | |
| Position-based proxy | Player position + team DEF_RATING | |
| Research this | Investigate per-position data availability | ✓ |

**User's choice:** Research this

---

## Pipeline Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| CLI command (manual) | Separate command after ingest | |
| Chained with ingest | Ingest auto-triggers features | ✓ |
| You decide | Claude's discretion | |

**User's choice:** Chained with ingest

---

## Season-Level Aggregate Features

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include | Season avg, games played, season std dev | |
| No, rolling is enough | L5/L10/L20 covers it | |
| You decide | Claude's discretion | ✓ |

**User's choice:** You decide

---

## Claude's Discretion

- Feature matrix format (wide vs long) — choose what works best with LightGBM
- Season-level aggregate features — include if valuable
- Module organization, file structure
- Parquet compression/partitioning
- Feature naming conventions
- Incomplete rolling window handling (NaN vs partial)

## Deferred Ideas

None — discussion stayed within phase scope
