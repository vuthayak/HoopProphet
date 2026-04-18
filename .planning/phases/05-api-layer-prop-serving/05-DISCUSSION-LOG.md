# Phase 5: API Layer & Prop Serving - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 05-CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-18
**Phase:** 05-api-layer-prop-serving
**Mode:** discuss

## Discussion Areas

### Default Line Derivation
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How should default stat lines be derived? | Median of recent games, Mean of recent games, Recent-form weighted (EMA), You decide | Median of recent games |
| Should lines be rounded to 0.5 or 0.1 increments? | 0.5 increments only (sportsbook style), 0.1 increments, You decide | 0.5 increments only |

### Top Prop Ranking
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How should top props be ranked? | Model probability, Combined probability + hit rate, You decide | Combined probability + hit rate |
| Which stats qualify as "known for" a player? | Filter by volume & relevance, Show all stats let ranking sort, You decide | Filter by volume & relevance |
| How should probability and hit rate combine? | Probability ranks, hit rates shown, Blended probability+hit_rate score, You decide | Probability ranks, hit rates shown |

### API Response Shape
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How much data in each response? | Lean JSON — only essential fields, Rich JSON — include player context, You decide | Lean JSON — only essential fields |
| Should probabilities be rounded? | Round to 1%, Full float precision, You decide | Round to 1% |
| Hit rate format? | Rate + sample count per window, Rate only per window | Rate + sample count per window |

### Edge Case Behavior
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| What when model artifact not loaded? | 200 with empty predictions, 503 Service Unavailable, You decide | 200 with empty predictions |
| What when player has <5 games in a window? | None for insufficient windows, Return data with insufficient flag, You decide | None for insufficient windows |
| What when player_id doesn't exist? | 404 for unknown player, You decide | 404 for unknown player |

### Feature Serving Strategy
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How should features be served for predictions? | Pre-computed from Parquet, On-the-fly from game logs, Hybrid | Pre-computed from Parquet |

### API URL Structure
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| What URL structure? | Flat /api prefix, Versioned /api/v1 prefix, You decide | Flat /api prefix |

### Health & Model Status
| Question | Options Presented | Answer |
|----------|-------------------|--------|
| Should health endpoint expose model status? | Simple health only, Health with model status | Health with model status |

## Prior Decisions Applied

From Phase 1: SQLite cache, no live NBA API calls, DNP row synthesis
From Phase 2: Rolling features L5/L10/L20, temporal .shift(1) guard, long-format features
From Phase 3: Unified LightGBM, binary classification, isotonic/Platt calibration, single .joblib artifact
From Phase 4: Walk-forward backtest, -110 vig, per-stat calibration curves

## Corrections Made

None — all recommendations were accepted as-is.

---

*Phase: 05-api-layer-prop-serving*
*Discussion logged: 2026-04-18*