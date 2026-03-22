# Project Research Summary

**Project:** HoopProphet V2
**Domain:** NBA prop betting analytics platform
**Researched:** 2026-03-22
**Confidence:** HIGH

## Executive Summary

HoopProphet V2 transforms a working but weak V1 prototype into a probability-based NBA prop betting analytics platform. The core pivot — from predicting raw stat values to predicting the probability of hitting over/under on a prop line — is well-supported by sports ML literature and is the approach used by every serious prop analytics tool. The recommended stack (LightGBM binary classifier + isotonic calibration + pandas feature engineering + SQLite/Parquet data caching) is battle-tested for tabular sports data at this scale and requires no new infrastructure beyond what V1 already runs.

The architecture splits cleanly into two subsystems: an offline training pipeline (data fetching → feature engineering → model training → artifact export) and an online serving layer (FastAPI loading a model artifact + cached data). This separation eliminates V1's fatal design flaw of retraining per request, and the component boundaries are well-defined with clear data contracts between layers. The existing React + FastAPI + Docker stack stays; new additions are LightGBM, recharts, and a SQLite caching layer.

The dominant risks are all data-science pitfalls, not engineering ones: probability miscalibration (showing "75%" when the true rate is 50%), time-series data leakage (features that accidentally include the outcome being predicted), survivor bias (training data that omits games where players didn't play), and random train/test splits (V1's current `RepeatedKFold` approach inflates accuracy by 10-20%). These are well-documented failure modes with known prevention strategies, but every one of them must be addressed explicitly — they won't be caught by standard software testing. The build order must front-load the data pipeline and feature engineering before model training, because garbage-in guarantees garbage-out regardless of model sophistication.

## Key Findings

### Recommended Stack

The V2 stack extends V1 (React, FastAPI, Docker) with ML and data tooling. No new infrastructure services required.

**Core technologies:**
- **LightGBM** (`objective='binary'`): Unified classification model — best tradeoff of speed, accuracy, and native categorical support for tabular sports data under 1M rows
- **scikit-learn CalibratedClassifierCV**: Isotonic regression calibration — ensures predicted probabilities match observed hit rates (non-negotiable for a betting platform)
- **SQLite + Parquet**: Dual-layer data cache — SQLite for raw NBA API responses (relational queries), Parquet for training-ready feature matrices (fast pandas bulk reads)
- **joblib**: Model serialization — load trained model + calibrator as single artifact at API startup
- **recharts**: Lightweight React charting — hit rate bars, trend visualization, calibration displays
- **pandas + numpy**: Feature engineering pipeline — rolling windows, opponent aggregations, consistency metrics (already in stack)

### Expected Features

**Must have (table stakes):**
- Player search with autocomplete (exists in V1)
- Prop line display with over/under framing and standard .5 increments
- Hit rate analysis across L5/L10/L20/season windows — the core value proposition
- Recent game log table — bettors verify data themselves
- Injury/availability flags — even basic keyword matching prevents bets on OUT players

**Should have (differentiators):**
- ML probability prediction — forward-looking, accounts for opponent/rest/form (key differentiator over stat-lookup tools)
- Dynamic prop selection — surface top 4-5 props per player ranked by probability
- Adjustable stat lines — slider for comparing different thresholds
- Daily best picks dashboard — the "just tell me what to bet" feature
- Back-testing results display — builds credibility with skeptical bettors
- Multi-window hit rate visualization with trend context

**Defer (v2+ / out of scope):**
- Sportsbook integration (legal complexity)
- Real-time live betting (different architecture entirely)
- Social features, bankroll management, AI text summaries (anti-features)
- Opponent context display (nice-to-have, not essential for launch)

### Architecture Approach

V2 splits into an offline training pipeline and an online serving API, connected by a model artifact file. The offline pipeline runs nightly: Data Fetcher pulls NBA API data into SQLite, Feature Builder transforms it into Parquet feature matrices, Model Trainer fits LightGBM and calibrates, then saves a `.joblib` artifact. The online API loads this artifact at startup and serves predictions from cache — no per-request training, no live NBA API calls for historical data.

**Major components:**
1. **Data Fetcher** — pulls game logs/team stats from NBA API into SQLite with retry logic and progress tracking
2. **Feature Builder** — transforms raw game logs into model-ready features (rolling averages, opponent defense, rest days, consistency metrics) with strict temporal guards (`.shift(1)`)
3. **Model Trainer + Calibrator** — trains unified LightGBM classifier, applies isotonic calibration, saves artifact with metrics
4. **Back-Testing Engine** — walk-forward evaluation across historical seasons with vig-adjusted profit metrics
5. **FastAPI Serving Layer** — new endpoints (`/player/{name}/props`, `/daily-picks`, `/backtest/summary`) serving from model + cache
6. **React Frontend** — component-based rebuild with pages (Player, Daily Picks, Backtest), recharts visualization, MUI components

### Critical Pitfalls

1. **Probability miscalibration** — LightGBM raw probabilities are overconfident on sports data. Must apply isotonic regression calibration and validate with reliability diagrams (predicted vs. observed frequency within ±3%). Recalibrate periodically, not once.

2. **Survivor bias (missing DNP rows)** — NBA API only returns games where a player appeared. Training data has zero examples of "player didn't play." Must cross-reference team schedules and synthesize zero-minute rows, or predictions for injured/resting players will be catastrophically wrong.

3. **Time-series data leakage** — Pandas rolling operations include the current row by default. Every feature computation must use `.shift(1)` so game N's features only contain data through game N-1. This single bug can inflate back-test accuracy from 55% to 75% and create false confidence.

4. **Random train/test splits** — V1 uses `RepeatedKFold` which shuffles temporal data. Must replace with `TimeSeriesSplit` or walk-forward validation. Random splits on sports data inflate metrics by 10-20%.

5. **NBA API rate limiting at scale** — Multi-season pulls for 450+ players require tens of thousands of calls to an unofficial, undocumented API. Must cache aggressively, implement exponential backoff with jitter, and add resumable progress tracking.

## Implications for Roadmap

Based on research, the build order must follow data dependencies: data layer → features → model → API → frontend. Each layer depends on the one before it. Attempting to build the frontend before the API has real data leads to rework; training a model before features are correct leads to misleading results.

### Phase 1: Data Pipeline & Caching Layer
**Rationale:** Everything downstream depends on reliable, complete data. V1 fetches live per-request with no caching — this must be solved first. The survivor bias pitfall and NBA API rate limiting pitfall both live here.
**Delivers:** SQLite cache of multi-season game logs, team stats, and player data. Resumable data fetcher with retry logic. Zero-minute row synthesis for DNP games. Data completeness validation.
**Addresses:** Multi-season historical data requirement, remove per-request API dependency, NBA API rate limiting pitfall, survivor bias pitfall.
**Avoids:** Pitfalls #2 (survivor bias) and #5 (rate limiting).

### Phase 2: Feature Engineering Pipeline
**Rationale:** The model is only as good as its features. This phase builds the training-ready feature matrix with strict temporal guards. The data leakage pitfall is the highest-risk item in the entire project and must be addressed here.
**Delivers:** Feature builder module producing Parquet matrices with rolling averages (L5/L10/L20), opponent defensive ratings, rest/B2B flags, consistency metrics, home/away, pace/tempo, minutes context features. All features use `.shift(1)`. Automated leakage tests.
**Addresses:** Rich feature engineering requirement, minutes context (Pitfall #7), temporal leakage prevention (Pitfall #3).
**Avoids:** Pitfalls #3 (leakage) and #7 (minutes context).

### Phase 3: Model Training & Calibration
**Rationale:** With clean features ready, train the unified LightGBM classifier with proper temporal validation. This is where the probability prediction differentiator comes to life.
**Delivers:** Unified LightGBM binary classifier trained across all players/props. Isotonic regression calibration. Walk-forward validation (not random splits). Model artifact saved as `.joblib`. Training script runnable via cron.
**Addresses:** Unified model requirement, probability prediction, model calibration, offline training pipeline.
**Avoids:** Pitfalls #1 (miscalibration), #4 (random splits), #6 (concept drift via retraining cadence).

### Phase 4: Back-Testing Engine
**Rationale:** Before exposing predictions to users, validate the model against historical data with honest metrics. This builds internal confidence and provides data for the trust-building backtest display feature.
**Delivers:** Walk-forward back-testing across held-out seasons. Calibration curves. Vig-adjusted ROI metrics (52.4% breakeven threshold). Season-by-season accuracy reports.
**Addresses:** Back-testing requirement, model validation, back-test display data.
**Avoids:** Pitfall #8 (back-test without vig).

### Phase 5: API Layer Updates
**Rationale:** With model artifacts and cached data ready, build the new API endpoints that the frontend will consume. Replace V1's per-request training with artifact-based serving.
**Delivers:** New endpoints: `/player/{name}/props`, `/player/{name}/gamelog`, `/player/{name}/news`, `/daily-picks`, `/backtest/summary`. Model loaded at startup. SQLite-backed player/team cache. Deprecate old `/predict` endpoint.
**Addresses:** Dynamic prop selection, hit rate analysis, daily picks API, news flags.

### Phase 6: News & Injury Flags
**Rationale:** Injury status is critical for bettors but is a standalone integration that doesn't block the core ML pipeline. Build it after the API layer is stable.
**Delivers:** Keyword-based news search (NewsAPI or RSS), player alert records in SQLite, `/player/{name}/news` endpoint population, injury/trade/arrest flagging.
**Addresses:** Keyword-based news/sentiment flags requirement.

### Phase 7: Frontend Rebuild
**Rationale:** With all API endpoints live and serving real data, rebuild the frontend from V1's monolithic App.js into a component-based architecture. This is the largest user-facing phase.
**Delivers:** Component-based React app with routing. PlayerPage (search + props + hit rates + game log + news flags), DailyPicksPage (today's best picks), BacktestPage (model accuracy). recharts visualizations. Adjustable stat line slider. MUI theme.
**Addresses:** Clean modern frontend, player search view, daily picks dashboard, adjustable stat lines, multi-window hit rate visualization, back-testing display.

### Phase 8: Polish & Hardening
**Rationale:** Final pass for UX polish, honest presentation (confidence intervals, sample sizes, data freshness timestamps), and operational hardening (structured logging, pinned dependencies, Docker updates).
**Delivers:** UX refinements from pitfalls research (confidence intervals, sample size display, "last updated" timestamps, DNP-likely gating). Structured logging. Pinned dependencies. Updated Docker Compose. Remove Gemini dependency cleanup.
**Addresses:** Remove Gemini dependency, technical debt items, UX pitfalls.

### Phase Ordering Rationale

- **Data before features before model** — strict dependency chain; you can't engineer features without data, can't train without features
- **Back-testing before API** — validates the model is worth serving; catches leakage/calibration issues before users see predictions
- **API before frontend** — frontend consumes API contracts; building UI without real endpoints means rework
- **News as standalone phase** — it's an integration with external APIs (NewsAPI/RSS) that doesn't block the core ML → serving pipeline
- **Frontend last among major phases** — maximizes the chance that API contracts are stable when the UI is built
- **Polish as final phase** — addresses UX refinements, operational concerns, and tech debt after core functionality works

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Feature Engineering):** Most complex domain logic — needs research into which specific NBA features have predictive power, optimal rolling window sizes, and how to compute opponent defense vs. position
- **Phase 6 (News & Injury Flags):** NewsAPI free tier limits and RSS feed reliability need validation; ESPN scraping fragility is a risk

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Pipeline):** Well-documented SQLite + nba_api patterns; pitfalls research already covers retry/caching strategy in detail
- **Phase 3 (Model Training):** LightGBM binary classification + isotonic calibration is a well-documented pattern
- **Phase 5 (API Layer):** Standard FastAPI endpoint additions with clear contracts from architecture research
- **Phase 7 (Frontend):** Standard React component architecture with MUI + recharts; architecture research provides full component tree

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | LightGBM + calibration is the consensus approach for sports prop prediction; all libraries are mature and well-documented |
| Features | HIGH | Table stakes vs. differentiator distinction is clear; feature dependency tree is well-mapped; anti-features correctly identified |
| Architecture | HIGH | Offline/online split is the standard pattern for ML serving; component boundaries and data flow are well-defined |
| Pitfalls | HIGH | Sourced from academic studies, practitioner blogs, nba_api GitHub issues, and V1 codebase audit; all 8 pitfalls have specific prevention strategies |

**Overall confidence:** HIGH

### Gaps to Address

- **NBA API reliability in Docker/cloud:** nba_api blocks some cloud IPs. Need to test data collection from the actual deployment environment early in Phase 1. If blocked, may need to pre-cache data locally or use a proxy.
- **NewsAPI free tier limits:** Free tier allows 100 requests/day and has a 24-hour delay on articles. May not be sufficient for game-day injury checks. Evaluate RSS feeds as primary source during Phase 6 planning.
- **Calibration sample size:** Isotonic regression needs 5K+ calibration samples to avoid overfitting. If early-season training data is insufficient, fall back to Platt scaling (logistic regression) which is more stable with smaller samples.
- **Daily picks computation time:** Pre-computing predictions for 450+ active players needs benchmarking. If it exceeds reasonable batch job time, may need to limit to players on today's schedule only.
- **Concept drift monitoring:** Research identifies the need for post-trade-deadline retraining, but no specific monitoring infrastructure is suggested. Phase 3/8 should address automated Brier Score tracking.

## Sources

### Primary (HIGH confidence)
- University of Bath study on calibration vs. accuracy in sports betting (2024) — calibration-optimized models produce 69.86% higher returns
- Kingsley Onoh — NBA prop model survivor bias and two-stage architecture
- nba_api GitHub issues (#405, #239, #320, #556, #470) — rate limiting, timeout, and data quality documentation
- López de Prado — purged cross-validation methodology for time-series financial/sports data
- HoopProphet V1 codebase audit (.planning/codebase/CONCERNS.md) — direct assessment of technical debt

### Secondary (MEDIUM confidence)
- WagerProof — cross-validation vs. backtesting for betting models; retraining frequency guidance
- Sports-AI.dev — Brier Score and calibration methodology
- Community consensus on LightGBM vs. XGBoost vs. neural networks for tabular sports data
- Feature engineering pitfalls and temporal leakage patterns (multiple practitioner sources)

### Tertiary (LOW confidence)
- NewsAPI free tier capabilities — needs validation during Phase 6; terms may have changed
- ESPN injury report scraping viability — fragile by nature, needs testing

---
*Research completed: 2026-03-22*
*Ready for roadmap: yes*
