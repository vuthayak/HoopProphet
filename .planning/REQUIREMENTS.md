# Requirements: HoopProphet V2

**Defined:** 2025-03-22
**Core Value:** Bettors can quickly identify high-probability player props backed by data — not gut feeling — so they know which bets are worth taking.

## v1 Requirements

Requirements for V2 release. Each maps to roadmap phases.

### Data Pipeline

- [x] **DATA-01**: System collects multi-season NBA game logs for all active players and caches in SQLite
- [x] **DATA-02**: System collects team stats (defensive ratings, pace) and caches in SQLite
- [x] **DATA-03**: System handles NBA API rate limits with exponential backoff and retry logic
- [x] **DATA-04**: Data fetcher is resumable — can pick up where it left off if interrupted
- [x] **DATA-05**: System synthesizes zero-minute rows for games where a player was on the roster but did not play (DNP/inactive)

### Feature Engineering

- [ ] **FEAT-01**: System computes rolling averages per stat across L5, L10, L20 game windows
- [ ] **FEAT-02**: System computes rolling standard deviation per stat (consistency metric)
- [ ] **FEAT-03**: System computes opponent defensive rating vs player position for each game
- [ ] **FEAT-04**: System computes rest days and back-to-back game flags
- [ ] **FEAT-05**: System computes home/away indicator
- [ ] **FEAT-06**: System computes team pace and opponent pace features
- [ ] **FEAT-07**: System computes minutes trend features (recent minutes average)
- [ ] **FEAT-08**: System computes historical matchup stats (player's average vs specific opponent)
- [ ] **FEAT-09**: All features use `.shift(1)` temporal guard — game N's features only contain data through game N-1
- [ ] **FEAT-10**: Feature matrix output as Parquet file with binary target column (over/under the line)

### Model Training

- [ ] **MODL-01**: Single unified LightGBM classifier trained across all players and all prop stat types
- [ ] **MODL-02**: Model uses `objective='binary'` and outputs calibrated probabilities
- [ ] **MODL-03**: Isotonic regression calibration applied via CalibratedClassifierCV on held-out validation set
- [ ] **MODL-04**: Model trained using temporal walk-forward split (not random k-fold)
- [ ] **MODL-05**: Trained model + calibrator saved as single `.joblib` artifact
- [ ] **MODL-06**: Training script runnable offline (nightly/weekly via cron or manual trigger)
- [ ] **MODL-07**: Training logs metrics: log loss, Brier score, calibration curve data

### Back-Testing

- [ ] **TEST-01**: Walk-forward back-testing across historical seasons (train on 1..N-1, test on N)
- [ ] **TEST-02**: Back-test reports calibration curves (predicted vs observed hit rates)
- [ ] **TEST-03**: Back-test reports season-by-season accuracy breakdown
- [ ] **TEST-04**: Back-test reports vig-adjusted ROI metrics (52.4% breakeven threshold)

### Prop Analysis

- [ ] **PROP-01**: User can view hit rates for a player's props across L5, L10, L20, and full season windows
- [ ] **PROP-02**: System displays default stat lines derived from player's recent performance (rounded to .5 increments)
- [ ] **PROP-03**: User can adjust stat lines via slider and see hit rates update
- [ ] **PROP-04**: System surfaces top 4-5 props each player is most known for (dynamic per player, ranked by probability)
- [ ] **PROP-05**: Each prop displays ML-predicted probability of hitting over the line
- [ ] **PROP-06**: User can view recent game log table for any player

### News & Availability

- [ ] **NEWS-01**: System searches for player news using keywords (injury, arrest, trade, questionable, doubtful, out, not playing)
- [ ] **NEWS-02**: System flags players with active news alerts (type + source + recency)
- [ ] **NEWS-03**: User sees injury/availability flags on the player page when relevant alerts exist

### Frontend

- [ ] **UI-01**: Frontend uses component-based architecture (pages, components, hooks — not monolithic App.js)
- [ ] **UI-02**: User can search for any active NBA player via autocomplete
- [ ] **UI-03**: Player page shows prop cards with hit rate charts, ML probability, and adjustable lines
- [ ] **UI-04**: Player page shows recent game log table
- [ ] **UI-05**: Player page shows news/injury flags when present
- [ ] **UI-06**: Back-test page shows model accuracy and calibration metrics
- [ ] **UI-07**: Frontend has clean, modern, data-focused dashboard design
- [ ] **UI-08**: Hit rate visualization uses bar charts across L5/L10/L20/season windows

### Cleanup

- [ ] **CLNP-01**: Remove Gemini AI summary dependency from backend
- [ ] **CLNP-02**: Replace per-request model training with model artifact loading at API startup
- [ ] **CLNP-03**: API serves player/team lists from SQLite cache instead of live NBA API calls

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Daily Picks

- **PICK-01**: User can view a daily dashboard of today's best picks across all players with games
- **PICK-02**: Daily picks ranked by probability and filterable by stat type
- **PICK-03**: Each pick links to the full player analysis page

### Sportsbook Comparison

- **ODDS-01**: User can compare model probability to FanDuel/sportsbook odds
- **ODDS-02**: System identifies +EV (positive expected value) bets based on odds vs probability gap
- **ODDS-03**: System displays implied probability from sportsbook odds

### Advanced Features

- **ADV-01**: Opponent context display (team defensive ranking vs position breakdown)
- **ADV-02**: Referee assignment impact on prop predictions
- **ADV-03**: Vegas opening lines as model input features
- **ADV-04**: Full NLP sentiment analysis replacing keyword search

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time live betting / in-game updates | Different architecture entirely; not pre-game prop analysis |
| User accounts / authentication | Local analytics tool; not a multi-user platform |
| Mobile app | Web-first; mobile deferred |
| Social features / chat | Not aligned with core analytics value |
| Bankroll management / bet tracking | Liability risk; users have their own strategies |
| AI-generated text summaries | V1 used Gemini for this; users want data, not prose |
| Bet placement / sportsbook integration | Legal complexity, licensing; HoopProphet is analytics only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| FEAT-01 | Phase 2 | Pending |
| FEAT-02 | Phase 2 | Pending |
| FEAT-03 | Phase 2 | Pending |
| FEAT-04 | Phase 2 | Pending |
| FEAT-05 | Phase 2 | Pending |
| FEAT-06 | Phase 2 | Pending |
| FEAT-07 | Phase 2 | Pending |
| FEAT-08 | Phase 2 | Pending |
| FEAT-09 | Phase 2 | Pending |
| FEAT-10 | Phase 2 | Pending |
| MODL-01 | Phase 3 | Pending |
| MODL-02 | Phase 3 | Pending |
| MODL-03 | Phase 3 | Pending |
| MODL-04 | Phase 3 | Pending |
| MODL-05 | Phase 3 | Pending |
| MODL-06 | Phase 3 | Pending |
| MODL-07 | Phase 3 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| PROP-01 | Phase 5 | Pending |
| PROP-02 | Phase 5 | Pending |
| PROP-03 | Phase 7 | Pending |
| PROP-04 | Phase 5 | Pending |
| PROP-05 | Phase 5 | Pending |
| PROP-06 | Phase 5 | Pending |
| NEWS-01 | Phase 6 | Pending |
| NEWS-02 | Phase 6 | Pending |
| NEWS-03 | Phase 6 | Pending |
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |
| UI-06 | Phase 7 | Pending |
| UI-07 | Phase 7 | Pending |
| UI-08 | Phase 7 | Pending |
| CLNP-01 | Phase 8 | Pending |
| CLNP-02 | Phase 5 | Pending |
| CLNP-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0

---
*Requirements defined: 2025-03-22*
*Last updated: 2026-03-22 after roadmap creation — all 46 requirements mapped to phases*
