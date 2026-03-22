# Feature Research

**Domain:** NBA prop betting analytics platform
**Researched:** 2026-03-22
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Probability display per prop** | Every competitor shows over/under probability or confidence score. Bettors won't trust "picks" without a number. | MEDIUM | LightGBM `.predict_proba()` output; must be calibrated (Platt/isotonic) so 70% means 70%. Raw model scores feel arbitrary without calibration. |
| **Hit rate across game windows (L5/L10/L20/season)** | Daily Fantasy Fuel, PropsWiz, PropEdge all show multi-window hit rates. It's the primary "proof" bettors use to validate a pick. | MEDIUM | Rolling window queries against game log history. L5/L10 are most used; L20 and season provide context. Display as percentages with visual indicators. |
| **Player search with prop breakdown** | Every tool lets you search a player and see their prop landscape. Entry point for player-specific research. | LOW | Already have search from V1. Extend results view to show top props with probabilities and hit rates instead of raw stat predictions. |
| **Daily picks / best bets dashboard** | PropEdge, DailyPropHub, PropsWiz all surface a ranked daily picks page. Bettors want a quick "what should I bet today?" without researching every player. | MEDIUM | Query model across all active players for today's games, rank by probability, surface top N. Requires knowing today's schedule and filtering to active games. |
| **Confidence ranking on picks** | PropCruncher (0-100 score), PropEdge (visual confidence), TrueEdge (10-factor score). Bettors need to prioritize across dozens of options. | LOW | Derive from model probability; display as percentage or tier (high/medium/low confidence). Don't invent a separate scoring system — probability IS the confidence. |
| **Over/Under direction with stat line** | Users expect to see "Over 24.5 Points — 73% probability" not just a raw number. The prop format (over/under + line + probability) is the industry standard display. | LOW | Pair model prediction direction with the stat line and probability. This is the atomic unit of the product's output. |
| **Opponent defensive context** | PropEdge and TrueEdge show matchup-level context. Bettors distrust picks that ignore who the opponent is. | MEDIUM | Already planned as a feature in V2. Show opponent rank against the stat category (e.g., "vs #3 defense against PG scoring"). Surface as context alongside each prop. |
| **Recent form / trend indicators** | Hot/cold streak detection is in PropEdge, PropCruncher, Daily Fantasy Fuel. Bettors look for momentum patterns. | LOW | Calculate from L5 game logs — simple streak count (hit X of last Y). Visual indicator (hot/cold/neutral) next to each prop. |
| **Game log history per player** | PropsWiz, PropEdge, PropCruncher all provide game-by-game logs. Bettors want to verify the data behind the numbers. | LOW | Already fetching game logs in V1 backend. Expose as a table with key stats per game, sortable. Serves as "show your work" for the model. |
| **Injury/availability status flags** | Every serious tool flags injuries. A pick on a player who's OUT is worthless and destroys trust. | MEDIUM | Keyword-based news search (injury, out, GTD, questionable, ruled out, load management). Display as badges/alerts on affected players. Not full NLP — keyword matching against news headlines. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Adjustable stat lines with live probability update** | PropsWiz has this but most tools don't. Lets users see "what if the line moves?" — slides the line up/down and instantly recalculates probability. Powerful for bettors shopping across books with different lines. | MEDIUM | Model predicts P(stat > line), so changing the line just changes the threshold. Slider UI that calls model (or pre-computed distribution) for new probability. Feels interactive and builds trust. |
| **Dynamic prop selection (top 4-5 per player)** | Most tools show all props. Automatically surfacing only the props a player is "known for" (high-volume stats with enough sample) cuts noise. A guard's rebounding prop is usually irrelevant. | MEDIUM | Analyze career game log variance and volume per stat category. Rank by consistency × relevance. Suppresses low-signal props that would dilute pick quality. |
| **Back-testing with historical accuracy proof** | Showstone backtests across 10+ seasons. Most tools just show current hit rates. Showing "our model would have hit 68% last season" builds trust that competitors can't match without doing the work. | HIGH | Run model predictions against held-out historical seasons. Display accuracy by stat category, confidence tier, and time period. This is the "proof" that converts skeptics. |
| **Model calibration transparency** | DailyPropHub shows model probability vs implied probability. Most tools hide their methodology. Showing a calibration curve ("when we say 70%, it hits 70%") is a trust differentiator. | MEDIUM | Platt scaling or isotonic regression on validation set. Display calibration plot on an "about our model" page. Update with each retrain cycle. Few competitors expose this. |
| **Contextual feature explainability** | PropEdge shows "why" the model likes a pick. Most tools are black boxes. Showing top contributing factors (e.g., "opponent allows 4th most assists, player on 3-game hot streak, well-rested") builds user understanding and trust. | HIGH | LightGBM feature importances per prediction (SHAP values or built-in importance). Display top 3-4 factors as plain-English tags alongside each pick. Meaningful UX effort to make ML interpretable. |
| **Teammate absence impact** | PropsWiz filters by "games with/without [teammate]." When a star is out, role players' props shift dramatically. Flagging this context is high-signal. | HIGH | Track roster context per game in training data. When a key teammate is flagged as out, surface it as context: "Without [player], averaging +4.2 PPG." Requires injury data cross-referencing with game logs. |
| **Performance by game condition splits** | Home/away, back-to-back, rest days. PropEdge and PropCruncher show splits. Adds "why" context that bettors value for validation. | MEDIUM | Group game logs by condition (home/away, rest days 0/1/2+, B2B). Show hit rates per split. Data already available in game logs — just needs aggregation and display. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time sportsbook odds comparison** | Users want to see odds from FanDuel, DraftKings etc. alongside picks. PropCruncher aggregates 45+ books. | Requires paid API access (OpticOdds, WagerAPI), complex legal landscape, constant data freshness. Scope explosion for V2 with zero revenue. | Focus on probability from our model. Defer odds integration to a future milestone once the core model proves value. |
| **Parlay builder / multi-leg combo tool** | Bettors love parlays. NBA Stat Spot has a parlay builder. | Parlay math (correlated legs, independent assumptions) is a separate complex problem. Doing it poorly gives bad advice. Massive UI scope for marginal V2 value. | Show individual prop probabilities. Users can mentally combine picks. Add parlay tools in V3 once single-prop accuracy is proven. |
| **Full NLP sentiment analysis on news** | "AI-powered news analysis" sounds impressive. Some tools claim it. | Keyword-based flagging catches 90% of actionable signals (injury, out, trade, suspended) at 5% of the complexity. NLP adds latency, API costs, and false positives on ambiguous sentiment. | Keyword-based news flagging with curated keyword list. Catches what matters (availability) without the complexity. |
| **Live in-game prop updates** | Real-time adjustments during games feel cutting-edge. | Pre-game prop analysis is the core use case. Live updates require streaming infrastructure, real-time model serving, and fundamentally different UX. Completely different product. | Stay pre-game focused. "Today's picks before tip-off" is the value proposition. |
| **User accounts and bet tracking** | Users want to track their betting history, ROI, and profit/loss. | Adds authentication, database, GDPR/privacy concerns, and significant infra for a local analytics tool. Shifts product from "analytics" to "portfolio management." | Keep it stateless for V2. Consider lightweight local storage bet tracking in V3 if demand exists. |
| **Automated betting / API integration with sportsbooks** | "Just place the bet for me." | Legal minefield. Regulatory exposure. Liability if the model is wrong and auto-bets lose money. No sportsbook offers public bet-placement APIs for third parties. | Present recommendations clearly. The user decides and places bets themselves. |
| **Chat-based AI advisor ("ask about any player")** | Gemini/ChatGPT integration feels trendy. V1 had Gemini summaries. | Adds latency, API costs, hallucination risk. Users want data, not AI-generated narratives. V1's Gemini dependency is being removed for good reason. | Structured data display with clear labels. Numbers speak louder than generated text for this audience. |

## Feature Dependencies

```
[Unified LightGBM Classification Model]
    └──requires──> [Multi-season Historical Data Pipeline]
    └──requires──> [Feature Engineering (opponent, rest, form, etc.)]
    └──enables──> [Probability Display Per Prop]
                      └──enables──> [Over/Under Direction + Stat Line]
                      └──enables──> [Confidence Ranking]
                      └──enables──> [Daily Picks Dashboard]
                      └──enables──> [Adjustable Stat Lines]

[Hit Rate Analysis (L5/L10/L20/Season)]
    └──requires──> [Game Log History Storage]
    └──enhances──> [Probability Display] (provides validation alongside model output)

[Dynamic Prop Selection]
    └──requires──> [Game Log History Storage]
    └──enhances──> [Player Search View] (reduces noise)
    └──enhances──> [Daily Picks Dashboard] (surfaces only relevant props)

[Injury/News Flags]
    └──independent (keyword search against news sources)
    └──enhances──> [Daily Picks Dashboard] (filters out unavailable players)
    └──enhances──> [Player Search View] (warns user before deep-diving injured player)

[Back-Testing Engine]
    └──requires──> [Unified LightGBM Classification Model]
    └──requires──> [Multi-season Historical Data]
    └──enables──> [Model Calibration Transparency]

[Contextual Explainability]
    └──requires──> [Unified LightGBM Classification Model]
    └──requires──> [Feature Engineering]

[Performance Splits (Home/Away, B2B)]
    └──requires──> [Game Log History Storage]
    └──enhances──> [Contextual Explainability]
```

### Dependency Notes

- **Model requires data pipeline:** The probability model can't exist without multi-season data and feature engineering. Data + features must come first.
- **All user-facing analytics depend on the model:** Probability display, confidence ranking, daily picks, and adjustable lines all need a working classification model.
- **Hit rates are independent of the model:** Calculated directly from game logs, not model output. Can be built before or in parallel with the model.
- **Injury flags are fully independent:** Keyword search has no dependency on the model or historical data pipeline.
- **Back-testing requires both model and historical data:** Must have a trained model AND held-out seasons to validate against.
- **Dynamic prop selection is a data analysis task:** Depends on game logs, not the model. Can be computed as part of data pipeline.

## MVP Definition

### Launch With (V2 Core)

Minimum viable milestone — what's needed to deliver the "probability-based prop analytics" pivot.

- [ ] **Unified LightGBM model with probability output** — the entire pivot depends on this
- [ ] **Probability display per prop (over/under + line + %)** — the core atomic output users see
- [ ] **Hit rate across L5/L10/L20/season windows** — primary validation signal bettors use
- [ ] **Dynamic prop selection (top 4-5 per player)** — cuts noise, focuses on relevant props
- [ ] **Player search view with prop breakdown** — primary entry point for individual research
- [ ] **Daily picks dashboard** — the "what should I bet today?" view
- [ ] **Confidence ranking on daily picks** — lets users prioritize
- [ ] **Opponent defensive context labels** — minimum matchup context
- [ ] **Recent form / streak indicators** — hot/cold visual cues
- [ ] **Injury/news keyword flags** — prevents recommending picks on unavailable players
- [ ] **Clean dashboard UI** — credibility requires polish; current monolithic App.js needs restructuring

### Add After Validation (V2.x)

Features to add once core probability engine is working and trusted.

- [ ] **Adjustable stat lines with live probability update** — once model is serving, slider UI is straightforward
- [ ] **Back-testing with historical accuracy proof** — builds trust, proves model quality
- [ ] **Model calibration transparency (calibration curve)** — once back-testing exists, calibration display follows
- [ ] **Performance splits (home/away, B2B, rest days)** — enriches context on individual player pages
- [ ] **Game log history table per player** — "show your work" for transparency

### Future Consideration (V3+)

Features to defer until the probability model is proven and the product has real users.

- [ ] **Contextual feature explainability (SHAP-based)** — needs UX investment to make ML interpretable
- [ ] **Teammate absence impact analysis** — requires cross-referencing injury data with game logs at scale
- [ ] **Sportsbook odds integration** — needs paid API, legal review, significant scope
- [ ] **Parlay probability calculator** — needs proven single-prop accuracy first
- [ ] **User accounts and bet tracking** — only if product grows beyond personal tool

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Unified LightGBM model + probability output | HIGH | HIGH | P1 |
| Probability display (over/under + line + %) | HIGH | LOW | P1 |
| Hit rate windows (L5/L10/L20/season) | HIGH | MEDIUM | P1 |
| Dynamic prop selection (top 4-5) | HIGH | MEDIUM | P1 |
| Daily picks dashboard | HIGH | MEDIUM | P1 |
| Confidence ranking | HIGH | LOW | P1 |
| Player search with prop breakdown | HIGH | LOW | P1 |
| Injury/news keyword flags | HIGH | MEDIUM | P1 |
| Opponent defensive context | MEDIUM | MEDIUM | P1 |
| Recent form / streak indicators | MEDIUM | LOW | P1 |
| Clean dashboard UI (component restructure) | HIGH | MEDIUM | P1 |
| Over/Under direction + stat line display | HIGH | LOW | P1 |
| Game log history table | MEDIUM | LOW | P1 |
| Adjustable stat lines + live probability | HIGH | MEDIUM | P2 |
| Back-testing engine + display | HIGH | HIGH | P2 |
| Model calibration transparency | MEDIUM | MEDIUM | P2 |
| Performance splits (home/away, B2B) | MEDIUM | MEDIUM | P2 |
| Contextual explainability (SHAP) | MEDIUM | HIGH | P3 |
| Teammate absence impact | MEDIUM | HIGH | P3 |
| Sportsbook odds integration | HIGH | HIGH | P3 |

**Priority key:**
- P1: Must have for V2 launch
- P2: Should have, add in V2.x after core is solid
- P3: Nice to have, future milestone consideration

## Competitor Feature Analysis

| Feature | PropEdge | PropsWiz | Daily Fantasy Fuel | PropCruncher | HoopProphet (Our Approach) |
|---------|----------|----------|-------------------|--------------|---------------------------|
| Probability/confidence display | LightGBM confidence score | Historical hit rate as proxy | Implied hit % from odds | 0-100 composite score | LightGBM calibrated probability — direct and honest |
| Hit rate windows | Rolling averages | L5/L10 with adjustable lines | L5/L10/season/H2H | Player history sparklines | L5/L10/L20/season — same coverage as best competitors |
| Daily picks | Up to 20 picks ranked by confidence | Cheat sheet with filters | Prop trends page | Edge Finder | Ranked daily dashboard — sorted by probability, filterable |
| Adjustable lines | No | Yes — core feature | No | No | Yes — slider UI with live probability recalculation |
| Back-testing proof | Claims verified hit rate | 8M+ datapoints referenced | Not prominent | Not prominent | Historical accuracy display per season/category — transparency focus |
| Injury flags | Not prominent | Not prominent | Not prominent | Not prominent | Keyword-based news flags — simple but effective |
| Prop selection logic | Shows all props | Shows all props | Shows all props | Shows all props | Auto-selects top 4-5 relevant props per player — noise reduction |
| Sportsbook odds | No (own model only) | Current lines shown | Cross-book comparison | 45+ books aggregated | Deferred — no paid API dependency in V2 |
| Explainability | "Why the model likes it" | Filter-based exploration | Not available | Edge percentage | Top factors per pick — planned for V3 |

## Sources

- **PropEdge** (propedge.bet) — LightGBM-based NBA prop tool, 76% verified hit rate, confidence-ranked picks
- **PropsWiz** (propswiz.com) — Adjustable lines, cheat sheet, 8M+ datapoints, $20/mo premium
- **Daily Fantasy Fuel** (dailyfantasyfuel.com) — L5/L10/season hit rates, PrizePicks/Underdog optimization, 5-min updates
- **PropCruncher** (propcruncher.com) — 45+ sportsbook aggregation, 0-100 composite scoring, edge finder
- **DailyPropHub** (dailyprophub.com) — ML + baseline probability, confidence index, model vs implied probability
- **Showstone** (showstone.io) — 10+ season backtesting, scouting reports, institutional-grade analytics
- **TrueEdge** (trueedge.bet) — 10-factor scoring, explicit win probability with odds/edge display
- **PropsMadness** (betsmart.co review) — 50+ filters, shot charts, matchup heatmaps, 40+ sportsbooks
- **EV Analytics** (evanalytics.com) — Player prop calculator, real-time odds tracking
- **NBA Stat Spot** (mitchelldawkins.com) — React/TypeScript, Recharts, parlay builder, bet tracking

---
*Feature research for: NBA prop betting analytics*
*Researched: 2026-03-22*
