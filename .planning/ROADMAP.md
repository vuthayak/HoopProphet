# Roadmap: HoopProphet V2

## Overview

HoopProphet V2 transforms a working-but-weak V1 prototype into a probability-based NBA prop betting analytics platform. The build follows a strict data dependency chain: data → features → model → back-test → API → news → frontend → polish. Each phase delivers a complete, verifiable layer that the next phase depends on. The core pivot — from predicting raw stat values to predicting the probability of hitting a prop line — requires getting the data and model foundations right before any user-facing work begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Pipeline & Caching** - Multi-season NBA data collection with SQLite caching, retry logic, and DNP row synthesis
- [ ] **Phase 2: Feature Engineering Pipeline** - Transform raw game logs into training-ready feature matrix with temporal integrity
- [ ] **Phase 3: Model Training & Calibration** - Unified LightGBM classifier with isotonic calibration and offline training pipeline
- [ ] **Phase 4: Back-Testing Engine** - Walk-forward historical validation with vig-adjusted ROI metrics
- [ ] **Phase 5: API Layer & Prop Serving** - New endpoints serving predictions, hit rates, and player data from cached artifacts
- [ ] **Phase 6: News & Injury Flags** - Keyword-based news search and player availability flagging
- [ ] **Phase 7: Frontend Rebuild** - Component-based React app with player analysis, back-test display, and hit rate visualization
- [ ] **Phase 8: Polish & Hardening** - Remove V1 technical debt and production-ready cleanup

## Phase Details

### Phase 1: Data Pipeline & Caching
**Goal**: System has complete, cached NBA data spanning multiple seasons ready for feature engineering
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. Multi-season game logs for all active players are stored in SQLite and queryable offline
  2. Team stats (defensive ratings, pace) are stored in SQLite alongside game logs
  3. Data fetcher recovers gracefully from interruptions and resumes without re-fetching completed data
  4. Zero-minute rows exist for games where a player was on the roster but did not play
  5. NBA API rate limits never cause data collection to fail permanently
**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Foundation: dependencies, SQLite DB layer, test infrastructure, NBA API client
- [ ] 01-02-PLAN.md — Data collectors: team rosters, schedules, advanced stats, player game logs
- [ ] 01-03-PLAN.md — DNP synthesis, CLI ingest orchestrator, integration tests

### Phase 2: Feature Engineering Pipeline
**Goal**: Raw game data is transformed into a training-ready feature matrix with strict temporal integrity
**Depends on**: Phase 1
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, FEAT-08, FEAT-09, FEAT-10
**Success Criteria** (what must be TRUE):
  1. Feature matrix contains rolling averages (L5, L10, L20) and standard deviations for every tracked stat
  2. Opponent defensive rating, rest days, home/away, pace, minutes trend, and matchup history features are computed per game
  3. Every feature for game N is computed using only data through game N-1 (no leakage)
  4. Output Parquet file includes binary over/under target column for each stat line
**Plans**: TBD

### Phase 3: Model Training & Calibration
**Goal**: A single unified model produces trustworthy probability predictions for any player prop
**Depends on**: Phase 2
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04, MODL-05, MODL-06, MODL-07
**Success Criteria** (what must be TRUE):
  1. One LightGBM classifier is trained across all players and prop types, outputting probabilities
  2. Predicted probabilities are calibrated via isotonic regression so "70% predicted" means ~70% observed hit rate
  3. Model is trained using temporal walk-forward splits, not random cross-validation
  4. Trained model + calibrator are saved as a single artifact loadable at serving time
  5. Training is runnable offline as a standalone script with logged metrics (log loss, Brier score)
**Plans**: TBD

### Phase 4: Back-Testing Engine
**Goal**: Model accuracy is validated against historical data with honest, bettor-relevant metrics
**Depends on**: Phase 3
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. Walk-forward back-test evaluates the model across held-out historical seasons
  2. Calibration curves show predicted vs. observed hit rates
  3. Season-by-season accuracy breakdown is available
  4. ROI metrics are vig-adjusted using the 52.4% breakeven threshold
**Plans**: TBD

### Phase 5: API Layer & Prop Serving
**Goal**: Backend API serves prop predictions, hit rates, and player data from cached artifacts
**Depends on**: Phase 3, Phase 4
**Requirements**: PROP-01, PROP-02, PROP-04, PROP-05, PROP-06, CLNP-02, CLNP-03
**Success Criteria** (what must be TRUE):
  1. API loads the trained model artifact at startup and serves predictions without per-request training
  2. Player and team data is served from SQLite cache, not live NBA API calls
  3. User can retrieve hit rates across L5, L10, L20, and season windows for any player's props
  4. API returns top 4-5 props per player ranked by probability, with default stat lines
  5. API serves recent game log data for any player
**Plans**: TBD

### Phase 6: News & Injury Flags
**Goal**: System flags player availability concerns so bettors don't wager on unavailable players
**Depends on**: Phase 5
**Requirements**: NEWS-01, NEWS-02, NEWS-03
**Success Criteria** (what must be TRUE):
  1. System searches for and finds player news matching injury/trade/arrest/availability keywords
  2. Players with active alerts are flagged with alert type, source, and recency
  3. News flags are accessible via API for display on player pages
**Plans**: TBD

### Phase 7: Frontend Rebuild
**Goal**: Users interact with a modern, component-based frontend to analyze player props and model performance
**Depends on**: Phase 5, Phase 6
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, PROP-03
**Success Criteria** (what must be TRUE):
  1. Frontend uses a component-based architecture with separate pages and reusable components (not monolithic App.js)
  2. User can search for any active NBA player via autocomplete and land on a player analysis page
  3. Player page shows prop cards with hit rate bar charts, ML probability, adjustable stat line slider, and recent game log
  4. Player page shows news/injury flags when alerts exist
  5. Back-test page displays model accuracy and calibration metrics
**Plans**: TBD
**UI hint**: yes

### Phase 8: Polish & Hardening
**Goal**: V1 technical debt is cleaned up and the system is production-ready
**Depends on**: Phase 7
**Requirements**: CLNP-01
**Success Criteria** (what must be TRUE):
  1. Gemini AI summary dependency is fully removed from the backend
  2. Application runs cleanly in Docker Compose with no deprecated V1 code paths
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Pipeline & Caching | 0/3 | Planning complete | - |
| 2. Feature Engineering Pipeline | 0/? | Not started | - |
| 3. Model Training & Calibration | 0/? | Not started | - |
| 4. Back-Testing Engine | 0/? | Not started | - |
| 5. API Layer & Prop Serving | 0/? | Not started | - |
| 6. News & Injury Flags | 0/? | Not started | - |
| 7. Frontend Rebuild | 0/? | Not started | - |
| 8. Polish & Hardening | 0/? | Not started | - |
