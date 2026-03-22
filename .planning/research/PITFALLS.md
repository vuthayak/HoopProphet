# Pitfalls Research

**Domain:** NBA prop betting analytics platform
**Researched:** 2026-03-22
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Optimizing for Accuracy Instead of Calibration

**What goes wrong:**
The unified LightGBM model achieves 58% accuracy on over/under classification but its predicted probabilities are meaningless — predicting 70% confidence on outcomes that hit only 45% of the time. Bettors trust the displayed probabilities, take bets with negative expected value, and lose money. The platform becomes useless despite "decent" accuracy numbers.

**Why it happens:**
Default ML training optimizes log loss or accuracy, not calibration. LightGBM's `binary` objective produces uncalibrated raw probabilities. Developers see 55-60% accuracy and declare success without checking whether the probability estimates themselves are reliable. A 2024 University of Bath study found calibration-optimized models produced 69.86% higher returns vs. accuracy-driven ones — the gap is enormous.

**How to avoid:**
- Use Brier Score and Expected Calibration Error (ECE) as primary metrics, not accuracy.
- Apply post-hoc calibration: Platt scaling (logistic regression on raw predictions) for well-separated classes, isotonic regression when you have 5K+ calibration samples. Start with Platt — isotonic overfits on smaller datasets.
- Build reliability diagrams (predicted probability vs. observed frequency) binned at 5% intervals. Every probability bin should be within ±3% of the diagonal.
- Recalibrate periodically, not once — calibration drifts as the season progresses.

**Warning signs:**
- Reliability diagram shows systematic S-curve or hockey-stick shape.
- High-confidence bins (>70%) have observed hit rates 15%+ lower than predicted.
- Mid-range predictions (40-60%) cluster at ~50% observed frequency regardless of predicted value.
- Brier Score decomposition shows high reliability component relative to resolution.

**Phase to address:**
ML model training phase (model calibration), verified again during back-testing phase.

---

### Pitfall 2: Survivor Bias — Training Only on Games Where Players Played

**What goes wrong:**
NBA API's `PlayerGameLog` endpoint only returns rows for games where a player appeared on the court. The training dataset contains zero examples of DNP (Did Not Play) outcomes. The model has "no idea what zero looks like" — it will predict Joel Embiid scoring 11 points in a game where he's listed OUT because it's never seen a zero-minute row. Every prop prediction implicitly assumes the player is active, which is catastrophically wrong for injured/resting players.

**Why it happens:**
The NBA API omits non-participation by design. Developers naively consume game log data without realizing missing games are invisible, not zero. This is the single most common mistake in NBA prop modeling, documented extensively by practitioners.

**How to avoid:**
- During data ingestion, cross-reference game logs against team schedules. For every team game where a player has no game log entry, synthesize a zero-minute row (0 PTS, 0 REB, 0 AST, etc.).
- Implement a two-stage architecture: Stage A (classifier) predicts play probability using injury reports, rest patterns, and schedule context. Stage B (regressor/classifier) runs props only for players predicted to play.
- At inference, if play probability < 0.5, return "DNP likely" instead of prop predictions.
- Consider filtering predictions for players with <20 predicted minutes — low-minute predictions have extreme variance.

**Warning signs:**
- Model never predicts very low stat lines (e.g., <3 points) for any player.
- Back-test shows predictions for games where the player was actually OUT/DNP.
- Training data has no rows with 0 minutes played.
- Minimum predicted value across all players is unreasonably high.

**Phase to address:**
Data pipeline / feature engineering phase (data ingestion must synthesize missing rows before model training begins).

---

### Pitfall 3: Time-Series Data Leakage in Feature Engineering

**What goes wrong:**
Rolling averages, momentum features, and opponent statistics include data from the game being predicted. The model sees a player's "last 5 games" average that includes tonight's game, learns to cheat, achieves 75%+ back-test accuracy, and collapses to coin-flip performance in production. This is the most insidious bug because it produces metrics that look spectacular.

**Why it happens:**
Pandas rolling operations default to including the current row. Without explicit `.shift(1)`, game N's features contain game N's outcome. This also happens when computing opponent defensive ratings — using season-long averages that include tonight's game, or computing team pace stats that weren't available at prediction time.

**How to avoid:**
- Every rolling/cumulative feature MUST use `.shift(1)` after computation so game N's features only contain data from games 1 through N-1.
- Implement a `feature_timestamp` audit: for every feature, document the latest data point it could contain, and verify it precedes the prediction timestamp.
- Opponent features must be computed as of the day before the game, not season-long averages.
- Normalize ALL feature engineering into a single pipeline with an explicit "as-of date" parameter. Never compute features ad-hoc.
- Add an automated leakage test: train on 2022-23, predict 2023-24. If accuracy exceeds 70% on binary over/under, suspect leakage.

**Warning signs:**
- Back-test accuracy dramatically higher than walk-forward accuracy (>10% gap).
- Model performance is suspiciously better than known benchmarks (closing lines are ~52-53% accurate for over/unders).
- Feature importance shows recent-game features dominating to an unrealistic degree.
- Performance degrades sharply when switching from back-test to live prediction.

**Phase to address:**
Feature engineering phase (strict `.shift(1)` policy), validated in back-testing phase.

---

### Pitfall 4: Random Train/Test Splits on Temporal Sports Data

**What goes wrong:**
Using standard `train_test_split` or k-fold cross-validation on game data shuffles games from 2024 into training and 2023 games into testing. The model trains on future data to predict past outcomes, inflating metrics by 10-20%. When deployed on truly future games, it underperforms massively. This is the V1 code's current approach with `RepeatedKFold`.

**Why it happens:**
Standard scikit-learn workflows default to random splitting. `RepeatedKFold(n_splits=10, n_repeats=10)` — which is what HoopProphet V1 uses — is designed for i.i.d. data, not time series. It feels rigorous (100 folds!) but is fundamentally wrong for temporal data.

**How to avoid:**
- Replace all random splits with chronological splits. Use `TimeSeriesSplit` from scikit-learn or implement walk-forward validation.
- Walk-forward: Train on seasons 2019-2022, validate on first half of 2022-23, test on second half of 2022-23. Slide window forward.
- For hyperparameter tuning, use purged cross-validation: add an embargo gap (5-10 games) between train and validation folds to prevent information bleed from autocorrelated game sequences.
- Hold out the most recent complete season entirely for final evaluation — never touch it during development.

**Warning signs:**
- Using `sklearn.model_selection.KFold` or `train_test_split` anywhere in the pipeline.
- Validation accuracy is suspiciously close to training accuracy.
- No explicit chronological ordering in the validation strategy.
- Performance on the held-out season is significantly worse than cross-validated metrics.

**Phase to address:**
ML model training phase (validation strategy), verified in back-testing phase.

---

### Pitfall 5: NBA API Rate Limiting and Data Collection Failures at Scale

**What goes wrong:**
Pulling multi-season game logs for 450+ players across 5 seasons requires tens of thousands of API calls. The NBA's unofficial API at `stats.nba.com` has undocumented rate limits, returns empty dataframes randomly, blocks cloud IP addresses, and periodically deprecates endpoints without notice. The data pipeline silently drops 15% of games, creating training data with hidden gaps. Alternatively, the pipeline hits rate limits, crashes halfway through, and leaves the dataset in an inconsistent state.

**Why it happens:**
`nba_api` wraps an unofficial, undocumented API. There's no SLA, no rate limit documentation, and no versioning guarantees. The NBA has been migrating to Next.js SSR patterns, embedding data in `__NEXT_DATA__` instead of API responses. Minimum safe delay between requests is 600ms, but even that fails intermittently. V1's current approach uses `time.sleep(1)` but has no retry logic, no caching, and no progress tracking.

**How to avoid:**
- Cache aggressively: store all API responses in a local SQLite/Parquet data lake. Never re-fetch data for completed games — box scores are immutable after finalization.
- Implement exponential backoff with jitter (start at 600ms, max 30s, 5 retries) using `tenacity` or similar library.
- Add progress tracking and resumption. If a pull crashes at player #237, resume from #237.
- Validate completeness: after each pull, compare expected game count (team schedule) against actual game log count. Flag gaps.
- Run data collection as a dedicated offline job, not inline with training or serving.
- Pin `nba_api` version and test against recorded fixtures to detect upstream API changes.

**Warning signs:**
- `HTTPSConnectionPool Read timed out` errors in logs.
- Inconsistent row counts between seasons (e.g., 2021-22 has 75% of expected games).
- `BoxScoreAdvancedV2` returning empty dataframes.
- Different results when re-running the same data pull.
- Failures that only occur in Docker/cloud but work locally.

**Phase to address:**
Data pipeline phase (caching, retry logic, validation), with ongoing monitoring.

---

### Pitfall 6: Concept Drift from Mid-Season Roster Changes and Role Shifts

**What goes wrong:**
A model trained on October-December data predicts February props using stale team context. A star player gets traded (e.g., a guard moves from a tanking team to a contender), their usage rate drops 8%, but the model still predicts based on their old role. Similarly, a backup becomes a starter due to injury, but the model still treats them as a 15-minute bench player. Props are systematically mispriced for players whose situations changed.

**Why it happens:**
Offline training creates a snapshot-in-time model. NBA rosters are volatile: the trade deadline reshuffles ~30-50 players, injuries promote backups, and coaching changes alter schemes. Features like "team pace" and "player usage" are aggregated across a context that no longer exists. Quarterly retraining (as recommended for "stable leagues") is too infrequent for the NBA's mid-season volatility.

**How to avoid:**
- Weight recent games exponentially higher than older games in feature computation. Use exponential moving averages (half-life of ~15 games) instead of simple rolling averages.
- Track roster transaction dates. When a player changes teams, reset their rolling features or apply a heavy discount to pre-trade data.
- Monitor calibration metrics weekly. Set alerts for Brier Score degradation >5% from baseline.
- Retrain at minimum monthly, plus triggered retraining after trade deadline and all-star break.
- Include "games since roster change" as a feature, and "team tenure" to let the model learn adjustment periods.

**Warning signs:**
- Prediction accuracy drops sharply in February (post-trade-deadline).
- Players who changed teams have systematically worse predictions.
- Calibration reliability diagrams skew after 30+ days since last retraining.
- Model still references team-specific features for players who were traded.

**Phase to address:**
Training pipeline phase (retraining cadence) and monitoring/deployment phase.

---

### Pitfall 7: Ignoring Minutes Context as the Gatekeeper of All Props

**What goes wrong:**
The model predicts "72% chance Jayson Tatum goes over 24.5 points" — but Tatum plays only 22 minutes in a blowout. All volume-based props (points, rebounds, assists, 3PM) are bounded by minutes played, yet the model treats props independently without conditioning on expected minutes. Blowout games, foul trouble, and rest-in-blowouts are invisible to the model.

**Why it happens:**
Points/rebounds/assists are the prediction targets, so developers focus on those directly. Minutes are treated as "just another feature" rather than as the fundamental constraint. NBA coaches routinely rest starters in the 4th quarter of blowout wins/losses, creating a bimodal minutes distribution that simple averages miss.

**How to avoid:**
- Build a minutes prediction sub-model (or at minimum include projected minutes as a first-class feature). Condition all prop probabilities on expected minutes.
- Include game spread as a feature — 10+ point favorites/underdogs have significantly different starter minutes distributions.
- Model the blowout risk: when spread > 8, expected minutes for starters drops ~4-6 minutes on average.
- Use game-over-probability curves to estimate garbage time risk.
- Consider a hierarchical approach: predict minutes first, then predict stats conditioned on those minutes.

**Warning signs:**
- Model consistently overestimates props for players on teams with large point spreads.
- Actual hit rates for favorites' starters are 5-10% lower than model predicts.
- No feature related to game spread, implied total, or blowout probability in the feature set.
- Error analysis shows worst predictions cluster in blowout games.

**Phase to address:**
Feature engineering phase (minutes context features), model training phase (hierarchical architecture consideration).

---

### Pitfall 8: Back-Testing Without Accounting for Vig and Line Movement

**What goes wrong:**
Back-test shows "+12% ROI" on historical props. In reality, sportsbooks charge ~4.5% vig (juice) on standard -110 lines, and lines move between opening and closing. The back-test used closing lines (look-ahead bias) and didn't deduct vig. True ROI is actually -3%. The platform shows "profitable" picks that lose money in practice.

**Why it happens:**
Academic ML evaluation ignores betting mechanics. Developers back-test against the stat line that was eventually set, not the line available when the bet would have been placed. Without sportsbook odds data (deferred to V3 in PROJECT.md), there's no vig to account for. But even without real odds, failing to simulate the vig creates dangerously misleading back-test results.

**How to avoid:**
- Apply a synthetic vig penalty in back-testing: assume every "bet" pays -110 (bet $110 to win $100). A model needs ~52.4% hit rate just to break even.
- When back-testing against prop lines, use lines available before game time (opening lines), not closing lines.
- Report back-test metrics that bettors understand: ROI after vig, hit rate relative to 52.4% breakeven, units won/lost, maximum drawdown.
- Clearly distinguish model accuracy (calibration quality) from betting profitability (requires beating the market + vig).
- Set honest expectations in UI: "high probability" ≠ "profitable bet" without knowing the odds.

**Warning signs:**
- Back-test ROI exceeds +5% without vig adjustment (suspiciously high).
- No breakeven threshold mentioned in evaluation.
- Results presented only as accuracy/AUC without betting-context metrics.
- Hit rate is 54% and labeled as "profitable" without vig calculation.

**Phase to address:**
Back-testing phase (vig simulation), UI/dashboard phase (honest presentation).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip calibration, ship raw LightGBM probabilities | Faster MVP launch | Users lose trust when "75% picks" hit 50%; rebuilding credibility is harder than building it | Never — calibration is table stakes for a betting platform |
| Use season-long averages instead of rolling features | Simpler feature pipeline, fewer edge cases | Model can't capture hot/cold streaks, recent role changes, or form shifts; predictions feel stale | Early prototyping only, must replace before user-facing |
| Fetch NBA data inline during training | No need to build a data lake | Pipeline breaks on rate limits, 2+ hour training runs, untestable without network, non-reproducible results | Never for a multi-season pipeline |
| Single `train_test_split` instead of walk-forward | Faster iteration during development | Inflated metrics, false confidence, potential leakage | Quick sanity checks only, never for reported metrics |
| Hardcode prop stat lines from current season averages | Skip the adjustable line feature | Lines don't reflect recent form; can't compare to sportsbook lines later | MVP only, replace with dynamic derivation |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `nba_api` PlayerGameLog | Assuming every team game has a player row (survivor bias) | Cross-reference team schedule; synthesize zero-minute rows for missing games |
| `nba_api` BoxScoreAdvancedV2 | Expecting consistent returns; endpoint periodically returns empty `{}` | Always validate response shape, implement retry with backoff, cache successful responses permanently |
| `nba_api` in Docker/cloud | Assuming it works the same as local — NBA blocks many cloud IPs | Test data collection from deployment environment early; consider proxy or pre-caching locally |
| `nba_api` historical data | Using live/advanced endpoints for pre-2019 data (they don't exist) | Use `PlayerGameLog` and `TeamGameLog` for historical data; advanced box scores only available post-2019 |
| `nba_api` multi-season pulls | Sequential calls with `time.sleep(1)` and no error recovery | Use exponential backoff, progress tracking, and resumable pulls; cache to Parquet/SQLite |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Computing features on-the-fly per prediction request | 2-5 second latency per player lookup | Pre-compute feature matrices nightly; serve from cache | >10 concurrent users |
| Storing game logs only in memory (DataFrames) | Works fast for 1 season; OOM at 5 seasons with advanced stats | Use Parquet files or SQLite as a persistent data lake | >3 seasons of data (~150K rows with features) |
| Retraining model on every schedule trigger without checking if data changed | Wasted compute, potential for training on stale cached data | Hash the training data; skip retraining if hash unchanged | Nightly retraining on static data wastes 30+ min/run |
| Loading full multi-season dataset into LightGBM without chunking | Memory spike during training; crashes on 8GB machines | Use LightGBM's native dataset chunking; train on Parquet with lazy loading | >500K training rows with 50+ features |
| Daily picks dashboard recomputing all 450+ players each request | 15+ minute response time; API timeout | Pre-compute daily picks in batch job; serve static results with TTL | First user request on any given day |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing raw model confidence scores with >2 decimal precision | Sophisticated users reverse-engineer the model by probing many players and reconstructing feature weights | Round probabilities to nearest 1%; limit API rate per client |
| Caching NBA API responses with player injury data without TTL | Stale injury data leads to predictions on OUT players; reputational damage | TTL of 1 hour max on injury/status data; always show "as of" timestamps |
| Storing model artifacts in publicly accessible Docker volume | Competitors extract your trained model weights | Keep model artifacts in non-mounted volume; don't expose /model/ endpoint |
| Logging full prediction requests with player names and lines | If logs leak, reveals your full feature set and prediction methodology | Log anonymized request IDs only; keep detailed logs in secured storage |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing probability without confidence interval | Users treat "68%" as gospel; don't understand model uncertainty | Show ranges: "65-72% likely" or use visual confidence indicators |
| Displaying too many props per player (8+) | Information overload; users can't identify best bets | Limit to top 4-5 highest-confidence props; let users expand if curious |
| Not showing the stat line the probability refers to | "72% over on points" — over what line? | Always display: "72% over 24.5 PTS" with the specific line prominent |
| Presenting historical hit rates without sample size | "80% hit rate L5" sounds amazing but N=5 is meaningless | Always show N alongside hit rate: "80% (4/5 L5)" and de-emphasize small samples |
| No indication of when data was last updated | Users don't know if predictions account for today's injury report | Show prominent "Last updated: 2h ago" and "Injury report reflected: Yes/No" |
| Showing predictions for players likely to sit | User bets on a player who's OUT; blames the platform | Gate predictions behind status check; prominently flag questionable/doubtful players |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Feature engineering:** Rolling averages computed — verify `.shift(1)` applied everywhere so current game isn't included
- [ ] **Model training:** LightGBM trained and shows 60% accuracy — verify calibration via reliability diagram, not just accuracy
- [ ] **Back-testing:** Reports "+8% ROI" — verify vig (52.4% breakeven) is accounted for and no look-ahead bias in features
- [ ] **Data pipeline:** 5 seasons of data loaded — verify completeness by comparing actual row counts against expected games per team schedule
- [ ] **Daily picks:** Dashboard shows today's picks — verify injury report is reflected and predictions filtered for OUT/doubtful players
- [ ] **Hit rate display:** "75% L10" shown for a prop — verify this was computed with `.shift(1)` and doesn't include the game being predicted
- [ ] **Prop line selection:** "Top 5 props" displayed — verify selection logic doesn't use future data or full-season stats unavailable at prediction time
- [ ] **Walk-forward validation:** "Model validated on 2023-24 season" — verify 2023-24 data was never used during feature engineering parameter selection or threshold tuning
- [ ] **Opponent defense features:** Included in model — verify they're computed as-of game date, not season-end aggregates
- [ ] **Retraining pipeline:** Runs nightly — verify it doesn't retrain on unchanged data, and recalibrates (not just refits) the model

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Probability miscalibration discovered post-launch | MEDIUM | Apply Platt scaling retroactively to existing model; update reliability diagrams; communicate uncertainty to users; no full retrain needed |
| Survivor bias in training data | HIGH | Must rebuild entire data pipeline to synthesize zero-minute rows; retrain model from scratch; all prior back-test results invalid |
| Feature leakage (`.shift(1)` missing) | HIGH | Audit every feature, fix leakage, retrain, re-run entire back-test; all prior accuracy claims invalid |
| NBA API endpoint deprecated mid-season | MEDIUM | Switch to alternative endpoint (V2→V3 or vice versa); cached historical data is safe; only live data affected |
| Concept drift after trade deadline | LOW | Trigger off-cycle retraining with post-deadline data weighted heavily; recalibrate; takes 1-2 days of new data |
| Back-test overfitting discovered | MEDIUM | Re-run with proper walk-forward validation; hold out most recent season; results will be worse but honest |
| Rate limiting blocks data pipeline | LOW | Increase delays, add jitter, switch to cached-first approach; historical data already cached is unaffected |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Accuracy over calibration | Model training + calibration phase | Reliability diagram within ±3% of diagonal; Brier Score decomposition shows low reliability component |
| Survivor bias (missing DNP rows) | Data pipeline / ingestion phase | Assert training data contains zero-minute rows; count matches team schedule game count |
| Feature leakage (`.shift(1)`) | Feature engineering phase | Automated test: no feature for game N contains data from game N; back-test accuracy within plausible range (<65%) |
| Random train/test splits | Model training phase (validation strategy) | Code review confirms `TimeSeriesSplit` or walk-forward; no `KFold` or `train_test_split` in pipeline |
| NBA API rate limiting | Data pipeline phase | Pipeline completes 5-season pull without crash; completeness check passes within 1% of expected |
| Concept drift | Training pipeline + monitoring phase | Weekly Brier Score tracking; automated alert if drift >5%; post-trade-deadline retraining documented |
| Minutes context missing | Feature engineering phase | Game spread / implied total in feature set; error analysis shows no blowout-game bias |
| Back-test without vig | Back-testing phase | All reported ROI figures include -110 vig penalty; breakeven threshold (52.4%) documented |
| LightGBM overfitting | Model training phase | Train/validation loss gap <5%; early stopping enabled; `min_data_in_leaf` ≥ 50 |

## Sources

- [University of Bath study on calibration vs. accuracy in sports betting (2024)](https://www.sportsbookadvisor.com/2025/12/06/why-90-of-value-bets-arent-actually-value-a-deep-dive-into-probability-calibration-in-sports-betting/) — HIGH confidence
- [Brier Score and calibration methodology for sports AI](https://www.sports-ai.dev/blog/ai-model-calibration-brier-score) — HIGH confidence
- [NBA prop model survivor bias and two-stage architecture (Kingsley Onoh)](https://kingsleyonoh.com/journal/nba-scenario-engine-usage-vacuum-modeling) — HIGH confidence
- [nba_api rate limiting and timeout issues (GitHub #405, #239, #320)](https://github.com/swar/nba_api/issues/405) — HIGH confidence
- [nba_api data quality / empty dataframe issues (GitHub #556, #470)](https://github.com/swar/nba_api/issues/556) — HIGH confidence
- [Purged cross-validation for time-series data (López de Prado)](https://en.wikipedia.org/wiki/Purged_cross-validation) — HIGH confidence
- [Walk-forward vs. cross-validation for betting models](https://wagerproof.bet/blog/cross-validation-vs-backtesting-betting-models) — MEDIUM confidence
- [Concept drift and retraining frequency for NBA models](https://wagerproof.bet/blog/when-to-retrain-betting-models-better-roi) — MEDIUM confidence
- [LightGBM overfitting hyperparameter tuning](https://readmedium.com/hyperparameter-tuning-to-reduce-overfitting-lightgbm-5eb81a0b464e) — MEDIUM confidence
- [Sports betting backtesting methodology and overfitting](https://www.betting-forum.com/threads/the-overfitting-problem-why-backtested-betting-systems-fail-in-production.47444/latest) — MEDIUM confidence
- [Feature engineering pitfalls and temporal leakage](https://medium.com/towards-data-engineering/feature-engineering-pitfalls-bias-leakage-and-the-illusion-of-model-performance-93d3cf343e8a) — MEDIUM confidence
- [HoopProphet V1 codebase concerns analysis](.planning/codebase/CONCERNS.md) — HIGH confidence (direct codebase audit)

---
*Pitfalls research for: NBA prop betting analytics platform*
*Researched: 2026-03-22*
