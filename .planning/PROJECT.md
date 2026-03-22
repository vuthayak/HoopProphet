# HoopProphet

## What This Is

A basketball analytics platform for sports bettors that predicts the probability of NBA player prop bets hitting. Users search for a player or browse a daily picks dashboard to see the top 4-5 props each player is most likely to hit, with hit rates across multiple game windows and adjustable stat lines. The model improves over time as more game data accumulates.

## Core Value

Bettors can quickly identify high-probability player props backed by data — not gut feeling — so they know which bets are worth taking.

## Requirements

### Validated

- ✓ NBA player and team search with autocomplete — V1
- ✓ Player headshot and team logo display from NBA CDN — V1
- ✓ Backend API serving player/team data via FastAPI — V1
- ✓ ML-based stat predictions using game log data — V1
- ✓ Prop line comparison (over/under vs career averages) — V1
- ✓ Docker Compose containerization (frontend + backend) — V1

### Active

- [ ] Unified LightGBM classification model trained across all players and props
- [ ] Probability prediction for over/under on stat lines (not raw stat values)
- [ ] Dynamic prop selection — surface top 4-5 props each player is known for
- [ ] Hit rate analysis across multiple game windows (L5, L10, L20, season)
- [ ] Adjustable stat lines — default derived from player data, user can slide up/down
- [ ] Rich feature engineering: opponent defense, rest/schedule, recent form, consistency, matchup history, pace/tempo, minutes context
- [ ] Offline training pipeline — nightly/weekly retrain, serve from saved model artifact
- [ ] Back-testing engine to validate model accuracy against past NBA seasons
- [ ] Keyword-based news/sentiment flags (injury, arrest, trade rumors, not playing)
- [ ] Player search view — search a player, see their probable picks with hit rates
- [ ] Daily best-picks dashboard — today's highest-probability picks across all players
- [ ] Clean, modern, data-focused frontend (dashboard style, minimal)
- [ ] Model calibration (Platt scaling or isotonic regression) so probabilities are trustworthy
- [ ] Multi-season historical data for training (not just current season)
- [ ] Remove Gemini AI summary dependency

### Out of Scope

- FanDuel/sportsbook odds comparison — deferred to future milestone, need to research data access first
- Real-time live game updates — not needed for pre-game prop analysis
- User accounts / authentication — local tool for now
- Mobile app — web-first
- Full NLP sentiment analysis — keyword-based flagging is sufficient for V2
- Referee assignment data — valuable but hard to source reliably, consider for V3
- Vegas opening lines as features — requires paid data source, defer until FanDuel milestone

## Context

**V1 state:** Working full-stack app with React frontend (monolithic 592-line App.js), FastAPI backend, and scikit-learn/XGBoost ML pipeline. V1 predicts raw stat values and compares to career averages. Model accuracy was weak due to per-player training on small samples (~60-80 rows), thin features, and model-switching between Linear Regression and XGBoost.

**V2 direction:** Pivot from "predict the stat" to "predict the probability of hitting a prop." One unified LightGBM model trained across all players on multi-season data. Core audience is sports bettors who want data-backed prop picks.

**Technical debt from V1:**
- Monolithic frontend (single App.js, no components)
- Full model retraining on every API request (no offline training)
- Print-based logging (no structured logging)
- Unpinned Python dependencies
- Duplicate `get_player_id` implementations
- No automated tests anywhere
- Gemini dependency for summaries (being removed)

**Data source:** NBA API (nba_api Python package) for game logs, player stats, team stats, career averages. No paid data sources in V2.

## Constraints

- **Data source**: NBA API (free, unofficial) — rate limits apply, need caching and respectful usage
- **Tech stack**: Keep React frontend + FastAPI backend + Docker Compose (proven in V1)
- **Model framework**: LightGBM for the unified classification model
- **Training**: Offline pipeline, not per-request — model artifact stored and served
- **No paid APIs**: V2 uses only free data sources; paid sportsbook data deferred

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pivot to probability prediction | Bettors care about "will it hit?" not exact stat values | — Pending |
| Single unified LightGBM model | Per-player models had tiny training sets (~60 rows); unified model gets 100K+ rows | — Pending |
| Binary classification framing | Directly outputs the probability users need; avoids indirect raw-stat prediction | — Pending |
| Offline training pipeline | V1's per-request training was slow and expensive; serve from saved model | — Pending |
| Drop Gemini summaries | Users want data, not AI-generated text; reduces external dependencies | — Pending |
| Keyword news search over full NLP | Simpler, faster, and captures the high-value signals (injury, out) without complexity | — Pending |
| Multi-season training data | More data = better generalization; enables back-testing against held-out seasons | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2025-03-22 after initialization*
