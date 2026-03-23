# Phase 1: Data Pipeline & Caching - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2025-03-22
**Phase:** 01-data-pipeline-caching
**Areas discussed:** Historical depth

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Historical depth | How many seasons back to collect? | ✓ |
| Collection workflow | How does the data fetcher run? | |
| Progress & monitoring | What do you see during collection? | |
| Data freshness | How often is data updated? | |

**User's choice:** Only historical depth — other areas deferred to Claude's discretion.

---

## Historical Depth

### Seasons of Data

| Option | Description | Selected |
|--------|-------------|----------|
| 3 seasons (~2022-2025) | Faster collection, current-era data only | |
| 5 seasons (~2020-2025) | Good balance of depth and speed | ✓ |
| 10 seasons (~2015-2025) | Deep history, captures player career arcs | |
| As many as possible | Maximum data, longest collection | |

**User's choice:** 5 seasons (~2020-2025)
**Notes:** None

### Player Coverage

**User's input (freeform):** Collect all 450+ active players for completeness since the app has a search bar for all players. Acknowledged that most users won't bet on non-rotation players, but wants full coverage.

### Recency vs Depth Concern

**User's input (freeform):** Raised concern that bettors rely on recent performance, not 5-year-old data. A 2020 player may perform very differently in 2026. Asked for this to be researched if not already covered.

**Claude's response:** Explained that rolling averages (L5/L10/L20) in Phase 2 handle recency naturally. Recommended sample weighting with recency decay as an additional safeguard. User agreed with this approach.

---

## Claude's Discretion

- Collection workflow (CLI script, Docker service, trigger mechanism)
- Progress visibility and monitoring
- Data refresh strategy
- SQLite schema design
- NBA API rate limiting details
- DNP row synthesis approach
- Data validation

## Deferred Ideas

None
